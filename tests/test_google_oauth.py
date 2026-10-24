"""
Tests for Google OAuth 2.0 / OpenID Connect authentication,
authorization logic, access requests, domain restrictions, and safety rules.
"""
from unittest.mock import patch
import pytest
from authlib.integrations.base_client.errors import MismatchingStateError
from services.oauth_service import oauth
from services import admin_service
from db import get_db_cursor
from blueprints.auth import is_safe_redirect_url
from tests.conftest import login_manager, login_clerk

def test_approved_clerk_google_login(client):
    """
    Approved clerk logs in via Google and gets clerk privileges (blocked from manager routes).
    """
    mock_token = {
        'userinfo': {
            'sub': 'clerk_sub_test_001',
            'email': 'clerk@grocerydb.local',
            'email_verified': True,
            'name': 'Counter Clerk',
            'picture': 'https://example.com/avatar_clerk.png'
        }
    }

    with patch.object(oauth.google, 'authorize_access_token', return_value=mock_token):
        res = client.get('/auth/google/callback', follow_redirects=True)
        assert res.status_code == 200
        assert b"CLERK" in res.data or b"Dashboard" in res.data
        
        # Verify clerk can access clerk routes
        orders_res = client.get('/orders')
        assert orders_res.status_code == 200

        # Verify clerk is blocked from manager-only routes
        admin_res = client.get('/admin/users')
        assert admin_res.status_code == 403

def test_approved_manager_google_login(client):
    """
    Approved manager logs in via Google and gets manager access.
    """
    mock_token = {
        'userinfo': {
            'sub': 'mgr_sub_test_002',
            'email': 'manager@grocerydb.local',
            'email_verified': True,
            'name': 'Store Manager',
            'picture': 'https://example.com/avatar_mgr.png'
        }
    }

    with patch.object(oauth.google, 'authorize_access_token', return_value=mock_token):
        res = client.get('/auth/google/callback', follow_redirects=True)
        assert res.status_code == 200
        assert b"MANAGER" in res.data or b"Dashboard" in res.data

        # Manager can access manager routes
        users_res = client.get('/admin/users')
        assert users_res.status_code == 200

        requests_res = client.get('/admin/access-requests')
        assert requests_res.status_code == 200

def test_unknown_email_creates_pending_request_and_gets_no_session(client):
    """
    Unknown email creates a pending access request and gets no logged-in session.
    """
    test_email = "new_applicant_99@example.com"
    mock_token = {
        'userinfo': {
            'sub': 'unknown_sub_777',
            'email': test_email,
            'email_verified': True,
            'name': 'Pending Applicant',
            'picture': 'https://example.com/pic.png'
        }
    }

    # Clean up any prior test request AND any stale user row, so this test is hermetic.
    with get_db_cursor('manager', commit=True) as (conn, cur):
        cur.execute("DELETE FROM access_requests WHERE email = %s;", (test_email,))
        cur.execute(
            "DELETE FROM app_users WHERE LOWER(email) = LOWER(%s) OR google_sub = %s;",
            (test_email, 'unknown_sub_777')
        )

    with patch.object(oauth.google, 'authorize_access_token', return_value=mock_token):
        res = client.get('/auth/google/callback', follow_redirects=False)
        assert res.status_code == 200
        assert b"Access Request Submitted" in res.data or b"Pending Authorization" in res.data
        
        # Verify no session was created
        with client.session_transaction() as sess:
            assert 'user_id' not in sess

        # Verify database has pending request
        pending_reqs = admin_service.get_pending_access_requests()
        matching = [r for r in pending_reqs if r['email'] == test_email]
        assert len(matching) == 1
        assert matching[0]['status'] == 'pending'

def test_unverified_email_is_rejected(client):
    """
    Unverified email from Google is rejected.
    """
    mock_token = {
        'userinfo': {
            'sub': 'unverified_sub_888',
            'email': 'unverified@example.com',
            'email_verified': False,
            'name': 'Unverified User'
        }
    }

    with patch.object(oauth.google, 'authorize_access_token', return_value=mock_token):
        res = client.get('/auth/google/callback', follow_redirects=True)
        assert res.status_code == 200
        assert b"Unverified Email" in res.data
        
        with client.session_transaction() as sess:
            assert 'user_id' not in sess

def test_deactivated_user_is_rejected(client):
    """
    Deactivated user account is rejected upon Google login.
    """
    deact_email = "deactivated_user@grocerydb.local"
    # Pre-create deactivated user
    with get_db_cursor('manager', commit=True) as (conn, cur):
        cur.execute("DELETE FROM app_users WHERE email = %s;", (deact_email,))
    
    uid = admin_service.preauthorize_user(deact_email, 'clerk', full_name='Deactivated Test')
    admin_service.toggle_user_status(uid, 0)  # Deactivate

    mock_token = {
        'userinfo': {
            'sub': 'deact_sub_333',
            'email': deact_email,
            'email_verified': True,
            'name': 'Deactivated Test'
        }
    }

    with patch.object(oauth.google, 'authorize_access_token', return_value=mock_token):
        res = client.get('/auth/google/callback', follow_redirects=True)
        assert res.status_code == 200
        assert b"Account Deactivated" in res.data
        
        with client.session_transaction() as sess:
            assert 'user_id' not in sess

def test_domain_restriction_works(client, app):
    """
    Domain restriction rejects unauthorized domains.
    """
    original_domains = app.config.get('ALLOWED_EMAIL_DOMAINS')
    app.config['ALLOWED_EMAIL_DOMAINS'] = ['grocerycompany.com']

    try:
        mock_token = {
            'userinfo': {
                'sub': 'external_sub_444',
                'email': 'intruder@othermail.com',
                'email_verified': True,
                'name': 'External Person'
            }
        }

        with patch.object(oauth.google, 'authorize_access_token', return_value=mock_token):
            res = client.get('/auth/google/callback', follow_redirects=True)
            assert res.status_code == 200
            assert b"Domain Not Allowed" in res.data
            
            with client.session_transaction() as sess:
                assert 'user_id' not in sess
    finally:
        app.config['ALLOWED_EMAIL_DOMAINS'] = original_domains

def test_last_manager_cannot_be_demoted_or_deactivated(client):
    """
    Safety rules: A manager cannot demote or deactivate themselves,
    and the last active manager cannot be demoted or removed.
    """
    login_manager(client)
    
    with client.session_transaction() as sess:
        mgr_id = sess['user_id']

    # Manager attempting to demote self
    demote_res = client.post(f'/admin/users/{mgr_id}/role', data={'role': 'clerk'}, follow_redirects=True)
    assert b"Safety rule" in demote_res.data or b"cannot" in demote_res.data

    # Manager attempting to deactivate self
    deact_res = client.post(f'/admin/users/{mgr_id}/toggle', follow_redirects=True)
    assert b"Safety rule" in deact_res.data or b"cannot" in deact_res.data

    # Direct service call to demote when single manager
    with pytest.raises(ValueError, match="Safety violation"):
        admin_service.update_user_role(mgr_id, 'clerk')

    with pytest.raises(ValueError, match="Safety violation"):
        admin_service.toggle_user_status(mgr_id, 0)

def test_existing_local_login_still_works(client):
    """
    Existing username/password fallback login still works seamlessly.
    """
    res = login_manager(client)
    assert res.status_code == 200
    assert b"Welcome back" in res.data or b"Dashboard" in res.data

    with client.session_transaction() as sess:
        assert sess.get('user_id') is not None
        assert sess.get('role') == 'manager'

def test_manager_access_request_approval_workflow(client):
    """
    Full workflow:
    1. Unknown user requests access via Google.
    2. Manager approves request as 'clerk'.
    3. User logs in again via Google and is successfully authenticated as clerk.
    """
    applicant_email = "new_intern_worker@example.com"
    applicant_sub = "google_sub_intern_111"

    # Clean up any leftover test data
    with get_db_cursor('manager', commit=True) as (conn, cur):
        cur.execute("DELETE FROM app_users WHERE email = %s;", (applicant_email,))
        cur.execute("DELETE FROM access_requests WHERE email = %s;", (applicant_email,))

    # Step 1: User requests access
    mock_token = {
        'userinfo': {
            'sub': applicant_sub,
            'email': applicant_email,
            'email_verified': True,
            'name': 'New Intern'
        }
    }
    with patch.object(oauth.google, 'authorize_access_token', return_value=mock_token):
        res = client.get('/auth/google/callback')
        assert res.status_code == 200

    # Retrieve request id from DB
    reqs = admin_service.get_pending_access_requests()
    matching_req = [r for r in reqs if r['email'] == applicant_email]
    assert len(matching_req) > 0
    req_id = matching_req[0]['id']

    # Step 2: Manager approves the request
    login_manager(client)
    approve_res = client.post(f'/admin/access-requests/{req_id}/approve', data={'role': 'clerk'}, follow_redirects=True)
    assert approve_res.status_code == 200
    assert b"approved" in approve_res.data.lower()

    # Step 3: Intern logs in via Google
    client.get('/logout')
    with patch.object(oauth.google, 'authorize_access_token', return_value=mock_token):
        login_res = client.get('/auth/google/callback', follow_redirects=True)
        assert login_res.status_code == 200
        assert b"CLERK" in login_res.data or b"Dashboard" in login_res.data
        
        with client.session_transaction() as sess:
            assert sess.get('email') == applicant_email
            assert sess.get('role') == 'clerk'

def test_state_mismatch_is_rejected(client):
    """
    A mismatching OAuth `state` (CSRF / expired session) is rejected with no session.
    """
    with patch.object(oauth.google, 'authorize_access_token', side_effect=MismatchingStateError()):
        res = client.get('/auth/google/callback', follow_redirects=True)
        assert res.status_code == 200
        assert b"Sign-In Session Expired" in res.data

        with client.session_transaction() as sess:
            assert 'user_id' not in sess

def test_is_safe_redirect_url_blocks_external_targets():
    """
    Open-redirect guard: only internal, single-slash paths are allowed.
    """
    assert is_safe_redirect_url('/dashboard') is True
    assert is_safe_redirect_url('/products?page=2') is True

    for bad in ('', None, 'https://evil.example.com', 'http://evil.example.com/x',
                '//evil.example.com', '/\\evil.example.com', '\\\\evil.example.com',
                'javascript:alert(1)'):
        assert is_safe_redirect_url(bad) is False, f"Should reject: {bad!r}"

def test_open_redirect_next_is_not_followed_after_login(client):
    """
    A malicious external `next` stored before login must not be followed; fall back to dashboard.
    """
    mock_token = {
        'userinfo': {
            'sub': 'clerk_sub_test_001',
            'email': 'clerk@grocerydb.local',
            'email_verified': True,
            'name': 'Counter Clerk',
        }
    }

    with client.session_transaction() as sess:
        sess['oauth_next'] = 'https://evil.example.com/steal'

    with patch.object(oauth.google, 'authorize_access_token', return_value=mock_token):
        res = client.get('/auth/google/callback')

    assert res.status_code == 302
    location = res.headers['Location']
    assert 'evil.example.com' not in location
    assert location.endswith('/dashboard')

    with client.session_transaction() as sess:
        assert sess.get('user_id') is not None

def test_internal_next_is_followed_after_login(client):
    """
    A safe internal `next` target is honored after a successful Google login.
    """
    mock_token = {
        'userinfo': {
            'sub': 'clerk_sub_test_001',
            'email': 'clerk@grocerydb.local',
            'email_verified': True,
            'name': 'Counter Clerk',
        }
    }

    with client.session_transaction() as sess:
        sess['oauth_next'] = '/products'

    with patch.object(oauth.google, 'authorize_access_token', return_value=mock_token):
        res = client.get('/auth/google/callback')

    assert res.status_code == 302
    assert res.headers['Location'].endswith('/products')

def test_google_login_endpoint_starts_flow(client, app):
    """
    GET /auth/google/login initiates the flow and stores only a safe internal next target.
    """
    from flask import redirect as flask_redirect

    original_id = app.config.get('GOOGLE_CLIENT_ID')
    original_secret = app.config.get('GOOGLE_CLIENT_SECRET')
    app.config['GOOGLE_CLIENT_ID'] = 'test-client-id.apps.googleusercontent.com'
    app.config['GOOGLE_CLIENT_SECRET'] = 'test-secret'

    def fake_authorize_redirect(redirect_uri, **kwargs):
        return flask_redirect('https://accounts.google.com/o/oauth2/v2/auth?fake=1')

    try:
        with patch.object(oauth.google, 'authorize_redirect', side_effect=fake_authorize_redirect):
            res = client.get('/auth/google/login?next=/products')
            assert res.status_code == 302
            assert 'accounts.google.com' in res.headers['Location']
            with client.session_transaction() as sess:
                assert sess.get('oauth_next') == '/products'

        # An external next must NOT be stored in the session.
        with patch.object(oauth.google, 'authorize_redirect', side_effect=fake_authorize_redirect):
            client.get('/auth/google/login?next=https://evil.example.com')
            with client.session_transaction() as sess:
                assert 'oauth_next' not in sess
    finally:
        app.config['GOOGLE_CLIENT_ID'] = original_id
        app.config['GOOGLE_CLIENT_SECRET'] = original_secret

def test_google_button_visibility_follows_configuration(client, app):
    """
    The 'Sign in with Google' button is hidden when unconfigured and shown when configured.
    """
    original_id = app.config.get('GOOGLE_CLIENT_ID')
    original_secret = app.config.get('GOOGLE_CLIENT_SECRET')
    try:
        app.config['GOOGLE_CLIENT_ID'] = ''
        app.config['GOOGLE_CLIENT_SECRET'] = ''
        hidden_res = client.get('/login')
        assert hidden_res.status_code == 200
        assert b"Continue with Google" not in hidden_res.data

        app.config['GOOGLE_CLIENT_ID'] = 'test-client-id.apps.googleusercontent.com'
        app.config['GOOGLE_CLIENT_SECRET'] = 'test-secret'
        shown_res = client.get('/login')
        assert shown_res.status_code == 200
        assert b"Continue with Google" in shown_res.data
    finally:
        app.config['GOOGLE_CLIENT_ID'] = original_id
        app.config['GOOGLE_CLIENT_SECRET'] = original_secret
