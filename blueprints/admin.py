"""
Admin blueprint for manager-only user management, access requests authorization,
and system audit logging.
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash
from auth import login_required, role_required
from services import admin_service
from logger import logger

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/admin/users')
@login_required
@role_required('manager')
def users_list():
    users = admin_service.get_users()
    pending_count = admin_service.get_pending_requests_count()
    return render_template('admin/users.html', users=users, pending_count=pending_count)

@admin_bp.route('/admin/users/create', methods=['POST'])
@login_required
@role_required('manager')
def create_user():
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '').strip()
    role = request.form.get('role', 'clerk').strip()
    email = request.form.get('email', '').strip() or None
    full_name = request.form.get('full_name', '').strip() or None

    if not username or not password:
        flash("Username and password are required.", "danger")
        return redirect(url_for('admin.users_list'))

    if len(password) < 6:
        flash("Password must be at least 6 characters long.", "danger")
        return redirect(url_for('admin.users_list'))

    if role not in ('manager', 'clerk'):
        flash("Role must be either manager or clerk.", "danger")
        return redirect(url_for('admin.users_list'))

    try:
        pw_hash = generate_password_hash(password)
        uid = admin_service.create_user(
            username=username,
            password_hash=pw_hash,
            role=role,
            created_by=session.get('username', 'manager'),
            email=email,
            full_name=full_name,
            auth_provider='local'
        )
        flash(f"User account '{username}' ({role.upper()}) created successfully (ID #{uid})!", "success")
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        if "Duplicate entry" in str(e) or "UNIQUE" in str(e).upper():
            flash(f"Username or email already exists. Please choose another.", "danger")
        else:
            flash(f"Failed to create user: {str(e)}", "danger")

    return redirect(url_for('admin.users_list'))

@admin_bp.route('/admin/users/preauthorize', methods=['POST'])
@login_required
@role_required('manager')
def preauthorize_user():
    email = request.form.get('email', '').strip()
    role = request.form.get('role', 'clerk').strip()
    full_name = request.form.get('full_name', '').strip() or None

    if not email or '@' not in email:
        flash("A valid email address is required for Google SSO pre-authorization.", "danger")
        return redirect(url_for('admin.users_list'))

    if role not in ('manager', 'clerk'):
        flash("Role must be either manager or clerk.", "danger")
        return redirect(url_for('admin.users_list'))

    try:
        uid = admin_service.preauthorize_user(
            email=email,
            role=role,
            full_name=full_name,
            created_by=session.get('username', 'manager')
        )
        flash(f"Google account '{email}' pre-authorized as {role.upper()} (User ID #{uid})! They can now log in immediately with Google.", "success")
    except Exception as e:
        logger.error(f"Error pre-authorizing Google email {email}: {e}")
        flash(f"Failed to pre-authorize user: {e}", "danger")

    return redirect(url_for('admin.users_list'))

@admin_bp.route('/admin/users/<int:user_id>/role', methods=['POST'])
@login_required
@role_required('manager')
def update_role(user_id: int):
    new_role = request.form.get('role', '').strip()
    if new_role not in ('manager', 'clerk'):
        flash("Invalid role selected.", "danger")
        return redirect(url_for('admin.users_list'))

    if user_id == session.get('user_id'):
        flash("Safety rule: You cannot demote or change your own role.", "warning")
        return redirect(url_for('admin.users_list'))

    try:
        admin_service.update_user_role(user_id, new_role, changed_by=session.get('username', 'manager'))
        flash(f"User #{user_id} role updated to {new_role.upper()}.", "success")
    except ValueError as ve:
        flash(str(ve), "danger")
    except Exception as e:
        flash(f"Failed to update role: {e}", "danger")

    return redirect(url_for('admin.users_list'))

@admin_bp.route('/admin/users/<int:user_id>/toggle', methods=['POST'])
@login_required
@role_required('manager')
def toggle_status(user_id: int):
    if user_id == session.get('user_id'):
        flash("Safety rule: You cannot deactivate your own active session account.", "warning")
        return redirect(url_for('admin.users_list'))

    user = admin_service.get_user_by_id(user_id)
    if not user:
        flash("User not found.", "danger")
        return redirect(url_for('admin.users_list'))

    new_status = 0 if user.get('is_active', 1) else 1
    try:
        admin_service.toggle_user_status(user_id, new_status, changed_by=session.get('username', 'manager'))
        action_word = "Activated" if new_status else "Deactivated"
        flash(f"User #{user_id} ({user['username']}) successfully {action_word}.", "info")
    except ValueError as ve:
        flash(str(ve), "danger")
    except Exception as e:
        flash(f"Failed to toggle status: {e}", "danger")

    return redirect(url_for('admin.users_list'))

# ----------------- ACCESS REQUESTS MANAGEMENT -----------------

@admin_bp.route('/admin/access-requests')
@login_required
@role_required('manager')
def access_requests_list():
    pending_requests = admin_service.get_pending_access_requests()
    all_requests = admin_service.get_all_access_requests(limit=100)
    return render_template('admin/access_requests.html',
                           pending_requests=pending_requests,
                           all_requests=all_requests)

@admin_bp.route('/admin/access-requests/<int:req_id>/approve', methods=['POST'])
@login_required
@role_required('manager')
def approve_request(req_id: int):
    role = request.form.get('role', 'clerk').strip()
    if role not in ('manager', 'clerk'):
        flash("Role must be clerk or manager.", "danger")
        return redirect(url_for('admin.access_requests_list'))

    try:
        user_id = admin_service.approve_access_request(
            request_id=req_id,
            role=role,
            reviewed_by=session.get('username', 'manager')
        )
        flash(f"Access request #{req_id} approved! User account activated as {role.upper()} (ID #{user_id}).", "success")
    except Exception as e:
        logger.error(f"Error approving access request #{req_id}: {e}")
        flash(f"Failed to approve request: {e}", "danger")

    return redirect(url_for('admin.access_requests_list'))

@admin_bp.route('/admin/access-requests/<int:req_id>/reject', methods=['POST'])
@login_required
@role_required('manager')
def reject_request(req_id: int):
    try:
        admin_service.reject_access_request(
            request_id=req_id,
            reviewed_by=session.get('username', 'manager')
        )
        flash(f"Access request #{req_id} has been rejected.", "info")
    except Exception as e:
        logger.error(f"Error rejecting access request #{req_id}: {e}")
        flash(f"Failed to reject request: {e}", "danger")

    return redirect(url_for('admin.access_requests_list'))

@admin_bp.route('/admin/audit-log')
@login_required
@role_required('manager')
def audit_log():
    table_filter = request.args.get('table', '').strip() or None
    action_filter = request.args.get('action', '').strip() or None
    logs = admin_service.get_audit_logs(limit=200, table_name=table_filter, action=action_filter)
    return render_template(
        'admin/audit_log.html',
        logs=logs,
        table_filter=table_filter,
        action_filter=action_filter
    )
