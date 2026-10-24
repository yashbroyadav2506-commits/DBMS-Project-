"""
Authentication blueprint handling local login, Google OAuth 2.0 / OpenID Connect,
logout, password change, and rate-limiting.
"""
import time
from urllib.parse import urlparse
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from werkzeug.security import check_password_hash, generate_password_hash
from authlib.integrations.base_client.errors import MismatchingStateError, OAuthError
from auth import login_required
from db import get_db_cursor, DatabaseUnreachableError
import mysql.connector
from services import admin_service
from services.oauth_service import oauth, is_google_oauth_configured
from logger import logger

auth_bp = Blueprint('auth', __name__)

# In-memory attempt tracker for rate limiting / lockout (5 consecutive failed attempts)
_failed_attempts = {}

def is_safe_redirect_url(target: str) -> bool:
    """
    Validates that a redirect URL is local to prevent open redirect vulnerabilities.
    Only internal, single-slash paths are allowed (no scheme, no protocol-relative
    '//host', no '/\\' trick, no backslashes).
    """
    if not target:
        return False
    if '\\' in target:
        return False
    if not target.startswith('/') or target.startswith('//'):
        return False
    # Reject any target carrying a scheme or netloc once parsed.
    parsed = urlparse(target)
    return not parsed.scheme and not parsed.netloc

def get_allowed_email_domains() -> list:
    """
    Reads the allowed email domain list from config, accepting both the singular
    ALLOWED_EMAIL_DOMAIN and plural ALLOWED_EMAIL_DOMAINS keys, given either as a
    comma-separated string or a list.
    """
    values = []
    for key in ('ALLOWED_EMAIL_DOMAINS', 'ALLOWED_EMAIL_DOMAIN'):
        raw = current_app.config.get(key)
        if not raw:
            continue
        if isinstance(raw, str):
            values.extend(raw.split(','))
        elif isinstance(raw, (list, tuple, set)):
            values.extend(raw)
    return sorted({v.strip().lower() for v in values if str(v).strip()})

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('dashboard.index'))

    client_ip = request.remote_addr or '127.0.0.1'

    # Check for temporary lockout (lockout for 60 seconds after 5 failures)
    attempt_info = _failed_attempts.get(client_ip, {'count': 0, 'locked_until': 0})
    if attempt_info['locked_until'] > time.time():
        remaining = int(attempt_info['locked_until'] - time.time())
        flash(f"Too many failed login attempts. Please wait {remaining} seconds before trying again.", "danger")
        return render_template('login.html', username='', google_configured=is_google_oauth_configured())

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        if not username or not password:
            flash("Username and password are required.", "danger")
            return render_template('login.html', username=username, google_configured=is_google_oauth_configured())

        try:
            with get_db_cursor('manager') as (conn, cursor):
                cursor.execute("""
                    SELECT id, username, email, full_name, avatar_url, password_hash, role, is_active, auth_provider 
                    FROM app_users 
                    WHERE username = %s;
                """, (username,))
                user = cursor.fetchone()

            if user and user['password_hash'] and check_password_hash(user['password_hash'], password):
                if not user.get('is_active', 1):
                    flash("Your account has been deactivated. Please contact the store manager.", "danger")
                    return render_template('login.html', username=username, google_configured=is_google_oauth_configured())

                # Reset failed attempts
                if client_ip in _failed_attempts:
                    del _failed_attempts[client_ip]

                # Regenerate session on login for session fixation protection
                session.clear()
                session['user_id'] = user['id']
                session['username'] = user['username']
                session['role'] = user['role']
                session['email'] = user.get('email')
                session['full_name'] = user.get('full_name') or user['username']
                session['avatar_url'] = user.get('avatar_url')
                session['auth_provider'] = user.get('auth_provider', 'local')
                session['last_active'] = time.time()

                admin_service.record_user_login(user['id'])
                admin_service.log_audit('app_users', 'LOGIN', user['id'], None, f"Local user {username} logged in successfully", username)
                flash(f"Welcome back, {session['full_name']}! Logged in as {user['role'].upper()}.", "success")
                
                next_page = request.args.get('next')
                if is_safe_redirect_url(next_page):
                    return redirect(next_page)
                return redirect(url_for('dashboard.index'))
            else:
                attempt_info['count'] += 1
                if attempt_info['count'] >= 5:
                    attempt_info['locked_until'] = time.time() + 60
                    _failed_attempts[client_ip] = attempt_info
                    flash("Account locked for 60 seconds due to 5 consecutive failed login attempts.", "danger")
                else:
                    _failed_attempts[client_ip] = attempt_info
                    remaining_attempts = 5 - attempt_info['count']
                    flash(f"Invalid username or password. ({remaining_attempts} attempts remaining before lockout)", "danger")

        except (DatabaseUnreachableError, mysql.connector.Error) as db_err:
            logger.critical(f"Database connection error during login: {db_err}")
            flash(
                "Unable to connect to the MySQL database. If deployed on Vercel, please ensure your cloud MySQL database "
                "(e.g. TiDB, Aiven, or AWS RDS) is configured in your Vercel Project Environment Variables (DB_HOST, DB_USER, DB_PASS).",
                "danger"
            )
        except Exception as e:
            logger.error(f"Error during login authentication: {e}")
            flash("An unexpected error occurred during login. Please try again.", "danger")

    return render_template(
        'login.html',
        username=request.form.get('username', ''),
        google_configured=is_google_oauth_configured()
    )

# ----------------- GOOGLE OAUTH 2.0 / OPENID CONNECT -----------------

@auth_bp.route('/auth/google')
@auth_bp.route('/auth/google/login')
def google_login():
    """
    Initiates Google OAuth 2.0 / OpenID Connect authorization code flow.
    Authlib attaches a per-session `state` and an OIDC `nonce` to the request.
    """
    if 'user_id' in session:
        return redirect(url_for('dashboard.index'))

    if not is_google_oauth_configured():
        flash("Google Sign-In is not configured yet. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in .env.", "warning")
        return redirect(url_for('auth.login'))

    # Store safe next url (only internal paths, prevents open redirects after login)
    next_page = request.args.get('next')
    if is_safe_redirect_url(next_page):
        session['oauth_next'] = next_page
    else:
        session.pop('oauth_next', None)

    redirect_uri = current_app.config.get('GOOGLE_REDIRECT_URI') or url_for('auth.google_callback', _external=True)
    return oauth.google.authorize_redirect(redirect_uri)

@auth_bp.route('/auth/google/callback')
def google_callback():
    """
    Handles Google OAuth 2.0 callback, verifies OpenID token and claims,
    and enforces role authorization rules.
    """
    client_ip = request.remote_addr or '127.0.0.1'

    # Check for OAuth error/cancellation
    error = request.args.get('error')
    if error:
        error_desc = request.args.get('error_description', 'Login was cancelled or rejected by Google.')
        logger.warning(f"Google OAuth error from {client_ip}: {error} ({error_desc})")
        return render_template('auth/auth_status.html',
                               status='cancelled',
                               title='Sign-In Cancelled',
                               message=f"Google sign-in was not completed ({error}). You can try again or use username/password.",
                               badge_class='warning')

    try:
        token = oauth.google.authorize_access_token()
        if not token:
            logger.warning(f"Google OAuth returned empty token for IP {client_ip}")
            return render_template('auth/auth_status.html',
                                   status='oauth_failure',
                                   title='Authentication Failed',
                                   message="Unable to retrieve authorization credentials from Google. Please try again.",
                                   badge_class='danger')
    except MismatchingStateError:
        # Authlib validated the per-session `state`; a mismatch indicates CSRF,
        # an expired session, or the flow being completed in another browser tab.
        logger.warning(f"Google OAuth state mismatch for IP {client_ip} (possible CSRF / expired session).")
        return render_template('auth/auth_status.html',
                               status='state_mismatch',
                               title='Sign-In Session Expired',
                               message="Your sign-in session expired or the security check failed. Please return to the login page and try again.",
                               badge_class='warning')
    except OAuthError as e:
        detail = str(e).lower()
        if 'nonce' in detail:
            logger.warning(f"Google OIDC nonce validation failed for IP {client_ip}: {e}")
            return render_template('auth/auth_status.html',
                                   status='nonce_mismatch',
                                   title='Sign-In Verification Failed',
                                   message="Google's identity response could not be verified (nonce mismatch). Please start the sign-in again.",
                                   badge_class='warning')
        logger.error(f"Google OAuth token exchange error: {e}")
        return render_template('auth/auth_status.html',
                               status='oauth_failure',
                               title='Authentication Error',
                               message="An unexpected error occurred while communicating with Google. Please try again later.",
                               badge_class='danger')
    except Exception as e:
        logger.error(f"Google OAuth token exchange error: {e}")
        return render_template('auth/auth_status.html',
                               status='oauth_failure',
                               title='Authentication Error',
                               message="An unexpected error occurred while communicating with Google. Please try again later.",
                               badge_class='danger')

    # Extract user claims from OpenID Connect token
    userinfo = token.get('userinfo')
    if not userinfo:
        try:
            userinfo = oauth.google.userinfo(token=token)
        except Exception:
            userinfo = {}

    google_sub = userinfo.get('sub')
    email = (userinfo.get('email') or '').strip().lower()
    email_verified = userinfo.get('email_verified', False)
    full_name = userinfo.get('name') or email.split('@')[0]
    avatar_url = userinfo.get('picture')

    if not google_sub or not email:
        logger.error(f"Incomplete Google user claims: sub={google_sub}, email={email}")
        return render_template('auth/auth_status.html',
                               status='oauth_failure',
                               title='Authentication Incomplete',
                               message="Google did not provide sufficient identity claims (email or user ID).",
                               badge_class='danger')

    # Rule 1: Email must be verified by Google
    if not email_verified:
        logger.warning(f"Unverified Google email attempted login: {email}")
        admin_service.log_audit('app_users', 'LOGIN_REJECT_UNVERIFIED', None, None, f"Unverified email: {email}", email)
        return render_template('auth/auth_status.html',
                               status='unverified',
                               title='Unverified Email',
                               message=f"The Google email address ({email}) is not verified. Please verify your email with Google and try again.",
                               badge_class='warning')

    # Rule 6: Optional domain restriction
    allowed_domains = get_allowed_email_domains()
    if allowed_domains:
        domain = email.split('@')[-1].lower() if '@' in email else ''
        if domain not in allowed_domains:
            logger.warning(f"Google login rejected due to disallowed domain {domain} for {email}")
            admin_service.log_audit('app_users', 'LOGIN_REJECT_DOMAIN', None, None, f"Disallowed domain: {domain} for {email}", email)
            return render_template('auth/auth_status.html',
                                   status='domain_restricted',
                                   title='Domain Not Allowed',
                                   message=f"Access is restricted to authorized email domains ({', '.join(allowed_domains)}). The domain '@{domain}' is not permitted.",
                                   badge_class='danger')

    # Rule 7: First-manager bootstrap
    initial_mgr_email = current_app.config.get('INITIAL_MANAGER_EMAIL', '').strip().lower()
    if initial_mgr_email and email == initial_mgr_email:
        user = admin_service.bootstrap_initial_manager(email, full_name, google_sub, avatar_url)
    else:
        # Rule 2: Lookup by google_sub, then fallback to email linking
        user = admin_service.find_user_by_google_sub(google_sub)
        if not user:
            user = admin_service.find_user_by_email(email)
            if user:
                admin_service.link_google_sub(user['id'], google_sub, avatar_url, full_name)
                user = admin_service.get_user_by_id(user['id'])

    # Rule 4: If no matching user exists in app_users, do NOT auto-create account with access
    if not user:
        req_id = admin_service.create_or_update_access_request(email, full_name, google_sub)
        logger.info(f"Created pending access request #{req_id} for Google user {email}")
        return render_template('auth/request_pending.html',
                               email=email,
                               full_name=full_name)

    # Rule 5: Check if user is deactivated
    if not user.get('is_active', 1):
        logger.warning(f"Deactivated user attempted Google login: {email} (ID #{user['id']})")
        admin_service.log_audit('app_users', 'LOGIN_REJECT_DEACTIVATED', user['id'], None, f"Deactivated login attempt: {email}", email)
        return render_template('auth/auth_status.html',
                               status='deactivated',
                               title='Account Deactivated',
                               message="Your account has been deactivated by the store manager. Please reach out to management for assistance.",
                               badge_class='danger')

    # Rule 3 & 8: Active matching user found -> log them in with stored role
    # Capture the validated post-login redirect target BEFORE regenerating the session,
    # otherwise session.clear() would discard it.
    next_page = session.get('oauth_next')

    # Regenerate session to protect against session fixation
    session.clear()
    session['user_id'] = user['id']
    session['username'] = user['username']
    session['role'] = user['role']
    session['email'] = user.get('email') or email
    session['full_name'] = user.get('full_name') or full_name
    session['avatar_url'] = avatar_url or user.get('avatar_url')
    session['auth_provider'] = 'google'
    session['last_active'] = time.time()

    admin_service.record_user_login(user['id'])
    admin_service.log_audit('app_users', 'LOGIN_GOOGLE', user['id'], None, f"Google login successful for {email} as {user['role']}", user['username'])
    flash(f"Welcome back, {session['full_name']}! Signed in via Google as {user['role'].upper()}.", "success")

    if is_safe_redirect_url(next_page):
        return redirect(next_page)
    return redirect(url_for('dashboard.index'))

@auth_bp.route('/logout')
def logout():
    username = session.get('username', 'Anonymous')
    session.clear()
    flash(f"You have been successfully logged out, {username}.", "info")
    return redirect(url_for('auth.login'))

@auth_bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    if session.get('auth_provider') == 'google' and not session.get('has_password', False):
        flash("You are signed in using Google SSO. Password management is handled by your Google account.", "info")
        return redirect(url_for('dashboard.index'))

    if request.method == 'POST':
        current_password = request.form.get('current_password', '').strip()
        new_password = request.form.get('new_password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()

        if not current_password or not new_password or not confirm_password:
            flash("All password fields are required.", "danger")
            return render_template('auth/change_password.html')

        if len(new_password) < 6:
            flash("New password must be at least 6 characters long.", "danger")
            return render_template('auth/change_password.html')

        if new_password != confirm_password:
            flash("New password and confirmation do not match.", "danger")
            return render_template('auth/change_password.html')

        user_id = session['user_id']
        with get_db_cursor('manager') as (conn, cursor):
            cursor.execute("SELECT password_hash FROM app_users WHERE id = %s;", (user_id,))
            user = cursor.fetchone()

        if not user or not user.get('password_hash') or not check_password_hash(user['password_hash'], current_password):
            flash("Current password is incorrect.", "danger")
            return render_template('auth/change_password.html')

        new_hash = generate_password_hash(new_password)
        admin_service.change_user_password(user_id, new_hash, session.get('username', 'user'))
        flash("Password updated successfully! Please keep your new password safe.", "success")
        return redirect(url_for('dashboard.index'))

    return render_template('auth/change_password.html')
