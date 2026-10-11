"""
Admin, Audit logging, User Management, and Access Requests service module.
"""
import re
import time
from typing import List, Dict, Any, Optional
from werkzeug.security import generate_password_hash
from db import get_db_cursor
from logger import logger

def log_audit(table_name: str, action: str, record_id: Optional[int], old_values: Optional[str], new_values: Optional[str], changed_by: str = 'system'):
    """
    Inserts a record into the audit_log table.
    """
    try:
        with get_db_cursor('manager', commit=True) as (conn, cursor):
            sql = """
                INSERT INTO audit_log (table_name, action, record_id, old_values, new_values, changed_by)
                VALUES (%s, %s, %s, %s, %s, %s);
            """
            cursor.execute(sql, (table_name, action, record_id, old_values, new_values, changed_by))
    except Exception as e:
        logger.error(f"Failed to write to audit_log: {e}")

def get_audit_logs(limit: int = 150, table_name: Optional[str] = None, action: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Retrieves recent audit logs with optional filtering.
    """
    with get_db_cursor('manager') as (conn, cursor):
        sql = "SELECT log_id, table_name, action, record_id, old_values, new_values, changed_by, created_at FROM audit_log WHERE 1=1"
        params = []
        if table_name:
            sql += " AND table_name = %s"
            params.append(table_name)
        if action:
            sql += " AND action = %s"
            params.append(action)
        sql += " ORDER BY log_id DESC LIMIT %s;"
        params.append(limit)
        cursor.execute(sql, tuple(params))
        return cursor.fetchall()

def get_users() -> List[Dict[str, Any]]:
    """
    Fetches all application users with OAuth details and metadata.
    """
    with get_db_cursor('manager') as (conn, cursor):
        cursor.execute("""
            SELECT id, username, email, full_name, avatar_url, auth_provider,
                   role, is_active, last_login, created_at
            FROM app_users 
            ORDER BY id ASC;
        """)
        return cursor.fetchall()

def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    """
    Fetches user by ID.
    """
    with get_db_cursor('manager') as (conn, cursor):
        cursor.execute("""
            SELECT id, username, email, full_name, avatar_url, auth_provider,
                   role, is_active, last_login, created_at, password_hash
            FROM app_users 
            WHERE id = %s;
        """, (user_id,))
        return cursor.fetchone()

def find_user_by_google_sub(google_sub: str) -> Optional[Dict[str, Any]]:
    """
    Looks up user by Google unique sub identifier.
    """
    if not google_sub:
        return None
    with get_db_cursor('manager') as (conn, cursor):
        cursor.execute("""
            SELECT id, username, email, full_name, avatar_url, auth_provider,
                   role, is_active, last_login, created_at
            FROM app_users 
            WHERE google_sub = %s;
        """, (google_sub,))
        return cursor.fetchone()

def find_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """
    Looks up user by normalized email address.
    """
    if not email:
        return None
    with get_db_cursor('manager') as (conn, cursor):
        cursor.execute("""
            SELECT id, username, email, full_name, avatar_url, auth_provider,
                   role, is_active, last_login, created_at, google_sub
            FROM app_users 
            WHERE LOWER(email) = LOWER(%s);
        """, (email.strip(),))
        return cursor.fetchone()

def link_google_sub(user_id: int, google_sub: str, avatar_url: Optional[str] = None, full_name: Optional[str] = None):
    """
    Links Google sub, avatar, and full name to an existing user account.
    """
    with get_db_cursor('manager', commit=True) as (conn, cursor):
        cursor.execute("""
            UPDATE app_users 
            SET google_sub = %s,
                avatar_url = COALESCE(%s, avatar_url),
                full_name = COALESCE(%s, full_name),
                auth_provider = 'google'
            WHERE id = %s;
        """, (google_sub, avatar_url, full_name, user_id))
    log_audit('app_users', 'LINK_GOOGLE', user_id, None, f"Linked google_sub: {google_sub}", 'oauth')

def record_user_login(user_id: int):
    """
    Updates last_login timestamp for a user.
    """
    try:
        with get_db_cursor('manager', commit=True) as (conn, cursor):
            cursor.execute("UPDATE app_users SET last_login = NOW() WHERE id = %s;", (user_id,))
    except Exception as e:
        logger.error(f"Failed to record user login timestamp: {e}")

def count_active_managers() -> int:
    """
    Counts active users with manager role to prevent orphan states.
    """
    with get_db_cursor('manager') as (conn, cursor):
        cursor.execute("SELECT COUNT(*) AS cnt FROM app_users WHERE role = 'manager' AND is_active = 1;")
        res = cursor.fetchone()
        return res['cnt'] if res else 0

def create_user(username: str, password_hash: Optional[str], role: str, created_by: str = 'manager',
                email: Optional[str] = None, full_name: Optional[str] = None, 
                auth_provider: str = 'local', google_sub: Optional[str] = None) -> int:
    """
    Creates a new user account and writes to audit log.
    """
    with get_db_cursor('manager', commit=True) as (conn, cursor):
        cursor.execute("""
            INSERT INTO app_users (username, password_hash, role, is_active, email, full_name, auth_provider, google_sub) 
            VALUES (%s, %s, %s, 1, %s, %s, %s, %s);
        """, (username, password_hash, role, email, full_name, auth_provider, google_sub))
        user_id = cursor.lastrowid
    log_audit('app_users', 'CREATE_USER', user_id, None, f"username: {username}, role: {role}, provider: {auth_provider}", created_by)
    return user_id

def update_user_role(user_id: int, new_role: str, changed_by: str = 'manager'):
    """
    Updates the role of a user with safety checks for last active manager.
    """
    user = get_user_by_id(user_id)
    if not user:
        raise ValueError("User not found.")
    
    old_role = user['role']
    if old_role == 'manager' and new_role != 'manager':
        if count_active_managers() <= 1 and user.get('is_active', 1):
            raise ValueError("Safety violation: Cannot demote the last remaining active manager.")

    with get_db_cursor('manager', commit=True) as (conn, cursor):
        cursor.execute("UPDATE app_users SET role = %s WHERE id = %s;", (new_role, user_id))
    log_audit('app_users', 'CHANGE_ROLE', user_id, f"role: {old_role}", f"role: {new_role}", changed_by)

def toggle_user_status(user_id: int, new_status: int, changed_by: str = 'manager'):
    """
    Deactivates or activates a user with safety check for last active manager.
    """
    user = get_user_by_id(user_id)
    if not user:
        raise ValueError("User not found.")

    if user['role'] == 'manager' and user.get('is_active', 1) and new_status == 0:
        if count_active_managers() <= 1:
            raise ValueError("Safety violation: Cannot deactivate the last remaining active manager.")

    with get_db_cursor('manager', commit=True) as (conn, cursor):
        cursor.execute("UPDATE app_users SET is_active = %s WHERE id = %s;", (new_status, user_id))
    status_str = "ACTIVE" if new_status else "DEACTIVATED"
    log_audit('app_users', 'TOGGLE_STATUS', user_id, None, f"status: {status_str}", changed_by)

def change_user_password(user_id: int, new_password_hash: str, changed_by: str):
    """
    Updates a user's password hash.
    """
    with get_db_cursor('manager', commit=True) as (conn, cursor):
        cursor.execute("UPDATE app_users SET password_hash = %s WHERE id = %s;", (new_password_hash, user_id))
    log_audit('app_users', 'PASSWORD_CHANGE', user_id, None, "Password updated", changed_by)

def _generate_unique_username(email: str, base_name: Optional[str] = None) -> str:
    """
    Generates a unique username based on email or name.
    """
    if base_name:
        candidate = re.sub(r'[^a-zA-Z0-9_]', '', base_name.lower().replace(' ', '_'))[:30]
    else:
        candidate = email.split('@')[0].lower()[:30]
    
    if not candidate:
        candidate = "user"

    with get_db_cursor('manager') as (conn, cursor):
        cursor.execute("SELECT id FROM app_users WHERE username = %s;", (candidate,))
        if not cursor.fetchone():
            return candidate

        # Append counter if conflict
        for i in range(1, 1000):
            test_username = f"{candidate}_{i}"[:50]
            cursor.execute("SELECT id FROM app_users WHERE username = %s;", (test_username,))
            if not cursor.fetchone():
                return test_username

    return f"{candidate}_{int(time.time())}"[:50]

def preauthorize_user(email: str, role: str, full_name: Optional[str] = None, created_by: str = 'manager') -> int:
    """
    Pre-authorizes a Google email address with a designated role before initial login.
    """
    clean_email = email.strip().lower()
    existing = find_user_by_email(clean_email)
    
    if existing:
        # Update existing user role and make sure account is active
        user_id = existing['id']
        with get_db_cursor('manager', commit=True) as (conn, cursor):
            cursor.execute("""
                UPDATE app_users 
                SET role = %s, is_active = 1, full_name = COALESCE(%s, full_name)
                WHERE id = %s;
            """, (role, full_name, user_id))
        log_audit('app_users', 'PREAUTHORIZE_UPDATE', user_id, f"role: {existing['role']}", f"role: {role}", created_by)
    else:
        username = _generate_unique_username(clean_email, full_name)
        user_id = create_user(
            username=username,
            password_hash=None,
            role=role,
            created_by=created_by,
            email=clean_email,
            full_name=full_name or username,
            auth_provider='google'
        )
        log_audit('app_users', 'PREAUTHORIZE_NEW', user_id, None, f"Preauthorized {clean_email} as {role}", created_by)

    # Automatically resolve any pending access request for this email
    with get_db_cursor('manager', commit=True) as (conn, cursor):
        cursor.execute("""
            UPDATE access_requests 
            SET status = 'approved', reviewed_by = %s, reviewed_at = NOW()
            WHERE LOWER(email) = LOWER(%s) AND status = 'pending';
        """, (created_by, clean_email))

    return user_id

def bootstrap_initial_manager(email: str, full_name: Optional[str], google_sub: str, avatar_url: Optional[str]) -> Dict[str, Any]:
    """
    Bootstraps the INITIAL_MANAGER_EMAIL as an active manager if not already configured.
    """
    clean_email = email.strip().lower()
    existing = find_user_by_email(clean_email)
    if existing:
        with get_db_cursor('manager', commit=True) as (conn, cursor):
            cursor.execute("""
                UPDATE app_users 
                SET role = 'manager', is_active = 1, google_sub = %s, 
                    avatar_url = COALESCE(%s, avatar_url), full_name = COALESCE(%s, full_name),
                    auth_provider = 'google'
                WHERE id = %s;
            """, (google_sub, avatar_url, full_name, existing['id']))
        log_audit('app_users', 'BOOTSTRAP_MANAGER', existing['id'], None, f"Bootstrap promoted {clean_email} to manager", 'bootstrap')
        return get_user_by_id(existing['id'])
    
    username = _generate_unique_username(clean_email, full_name)
    user_id = create_user(
        username=username,
        password_hash=None,
        role='manager',
        created_by='bootstrap',
        email=clean_email,
        full_name=full_name or 'Initial Store Manager',
        auth_provider='google',
        google_sub=google_sub
    )
    with get_db_cursor('manager', commit=True) as (conn, cursor):
        cursor.execute("UPDATE app_users SET avatar_url = %s WHERE id = %s;", (avatar_url, user_id))
    log_audit('app_users', 'BOOTSTRAP_MANAGER', user_id, None, f"Bootstrap created new manager {clean_email}", 'bootstrap')
    return get_user_by_id(user_id)

# ----------------- ACCESS REQUESTS MANAGEMENT -----------------

def get_pending_access_requests() -> List[Dict[str, Any]]:
    """
    Returns all pending user access requests.
    """
    with get_db_cursor('manager') as (conn, cursor):
        cursor.execute("""
            SELECT id, email, full_name, google_sub, requested_at, status
            FROM access_requests
            WHERE status = 'pending'
            ORDER BY requested_at DESC;
        """)
        return cursor.fetchall()

def get_pending_requests_count() -> int:
    """
    Returns the count of pending access requests for the manager navbar badge.
    """
    with get_db_cursor('manager') as (conn, cursor):
        cursor.execute("SELECT COUNT(*) AS cnt FROM access_requests WHERE status = 'pending';")
        res = cursor.fetchone()
        return res['cnt'] if res else 0

def get_all_access_requests(limit: int = 100) -> List[Dict[str, Any]]:
    """
    Returns all access requests (pending, approved, rejected) for the manager overview.
    """
    with get_db_cursor('manager') as (conn, cursor):
        cursor.execute("""
            SELECT id, email, full_name, google_sub, requested_at, status, reviewed_by, reviewed_at
            FROM access_requests
            ORDER BY id DESC
            LIMIT %s;
        """, (limit,))
        return cursor.fetchall()

def get_access_request_by_id(request_id: int) -> Optional[Dict[str, Any]]:
    """
    Gets single access request by ID.
    """
    with get_db_cursor('manager') as (conn, cursor):
        cursor.execute("SELECT id, email, full_name, google_sub, requested_at, status FROM access_requests WHERE id = %s;", (request_id,))
        return cursor.fetchone()

def create_or_update_access_request(email: str, full_name: Optional[str], google_sub: str) -> int:
    """
    Records a pending access request for an unknown Google user.
    If a pending request exists, updates it; otherwise inserts a new one.
    """
    clean_email = email.strip().lower()
    with get_db_cursor('manager', commit=True) as (conn, cursor):
        cursor.execute("""
            SELECT id FROM access_requests 
            WHERE LOWER(email) = LOWER(%s) AND status = 'pending';
        """, (clean_email,))
        existing = cursor.fetchone()
        
        if existing:
            req_id = existing['id']
            cursor.execute("""
                UPDATE access_requests 
                SET full_name = COALESCE(%s, full_name), 
                    google_sub = %s, 
                    requested_at = NOW()
                WHERE id = %s;
            """, (full_name, google_sub, req_id))
        else:
            cursor.execute("""
                INSERT INTO access_requests (email, full_name, google_sub, status)
                VALUES (%s, %s, %s, 'pending');
            """, (clean_email, full_name, google_sub))
            req_id = cursor.lastrowid
            
    log_audit('access_requests', 'REQUEST_ACCESS', req_id, None, f"New access request from {clean_email} ({full_name})", clean_email)
    return req_id

def approve_access_request(request_id: int, role: str, reviewed_by: str = 'manager') -> int:
    """
    Approves an access request: creates or activates the user account with chosen role,
    marks request approved, and logs audit record.
    """
    req = get_access_request_by_id(request_id)
    if not req:
        raise ValueError("Access request not found.")
    if req['status'] != 'pending':
        raise ValueError(f"Request is already {req['status']}.")
    if role not in ('manager', 'clerk'):
        raise ValueError("Role must be 'manager' or 'clerk'.")

    email = req['email'].strip().lower()
    google_sub = req.get('google_sub')
    full_name = req.get('full_name')

    # Look up existing user by google_sub or email
    user = find_user_by_google_sub(google_sub) if google_sub else None
    if not user:
        user = find_user_by_email(email)

    if user:
        user_id = user['id']
        with get_db_cursor('manager', commit=True) as (conn, cursor):
            cursor.execute("""
                UPDATE app_users 
                SET role = %s, 
                    is_active = 1,
                    google_sub = COALESCE(%s, google_sub),
                    full_name = COALESCE(%s, full_name),
                    auth_provider = 'google'
                WHERE id = %s;
            """, (role, google_sub, full_name, user_id))
    else:
        username = _generate_unique_username(email, full_name)
        user_id = create_user(
            username=username,
            password_hash=None,
            role=role,
            created_by=reviewed_by,
            email=email,
            full_name=full_name or username,
            auth_provider='google',
            google_sub=google_sub
        )

    # Update request status to approved
    with get_db_cursor('manager', commit=True) as (conn, cursor):
        cursor.execute("""
            UPDATE access_requests 
            SET status = 'approved', reviewed_by = %s, reviewed_at = NOW()
            WHERE id = %s;
        """, (reviewed_by, request_id))

    log_audit('access_requests', 'APPROVE_ACCESS', request_id, "status: pending", f"status: approved, role: {role}, user_id: {user_id}", reviewed_by)
    return user_id

def reject_access_request(request_id: int, reviewed_by: str = 'manager'):
    """
    Rejects an access request and records audit log.
    """
    req = get_access_request_by_id(request_id)
    if not req:
        raise ValueError("Access request not found.")
    if req['status'] != 'pending':
        raise ValueError(f"Request is already {req['status']}.")

    with get_db_cursor('manager', commit=True) as (conn, cursor):
        cursor.execute("""
            UPDATE access_requests 
            SET status = 'rejected', reviewed_by = %s, reviewed_at = NOW()
            WHERE id = %s;
        """, (reviewed_by, request_id))

    log_audit('access_requests', 'REJECT_ACCESS', request_id, "status: pending", "status: rejected", reviewed_by)
