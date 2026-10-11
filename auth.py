import time
from functools import wraps
from flask import session, redirect, url_for, flash, render_template, request

SESSION_TIMEOUT_SECONDS = 3600  # 60 minutes of inactivity

def check_session_timeout() -> bool:
    """
    Checks if the session has timed out due to inactivity.
    Returns True if session timed out and was cleared.
    """
    if 'user_id' in session:
        last_active = session.get('last_active')
        current_time = time.time()
        if last_active and (current_time - last_active > SESSION_TIMEOUT_SECONDS):
            session.clear()
            flash("Your session has expired due to inactivity. Please log in again.", "warning")
            return True
        session['last_active'] = current_time
    return False

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if check_session_timeout():
            return redirect(url_for('auth.login', next=request.url))
        if 'user_id' not in session:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for('auth.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def role_required(*allowed_roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if check_session_timeout():
                return redirect(url_for('auth.login'))
            if 'user_id' not in session:
                flash("Please log in to access this page.", "warning")
                return redirect(url_for('auth.login'))
            
            user_role = session.get('role')
            if user_role not in allowed_roles:
                flash(f"Access denied: '{user_role.capitalize() if user_role else 'User'}' role is not authorized for this page.", "danger")
                return render_template('403.html', title="403 - Forbidden"), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator
