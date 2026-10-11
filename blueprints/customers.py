"""
Customer management blueprint for viewing customers, editing, adding, and viewing customer purchase histories.
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from auth import login_required, role_required
from services import customer_service
from logger import logger

customers_bp = Blueprint('customers', __name__)

@customers_bp.route('/customers')
@login_required
def index():
    user_role = session.get('role', 'clerk')
    search_query = request.args.get('q', '').strip()
    customers = customer_service.get_customers(search_query=search_query, role=user_role)
    return render_template('customers/list.html', customers=customers, search_query=search_query)

@customers_bp.route('/customers/add', methods=['GET', 'POST'])
@login_required
def add():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        phone = request.form.get('phone', '').strip()
        city = request.form.get('city', '').strip()

        if not name:
            flash("Customer name is required.", "danger")
        else:
            try:
                cid = customer_service.add_customer(name, phone, city, changed_by=session.get('username', 'user'))
                flash(f"Customer '{name}' added successfully (ID #{cid})!", "success")
                return redirect(url_for('customers.index'))
            except Exception as e:
                logger.error(f"Error adding customer: {e}")
                flash(f"Failed to add customer: {str(e)}", "danger")

    return render_template('customers/form.html', action='Add', customer=None)

@customers_bp.route('/customers/edit/<int:customer_id>', methods=['GET', 'POST'])
@login_required
@role_required('manager')
def edit(customer_id: int):
    customer = customer_service.get_customer_by_id(customer_id, role='manager')
    if not customer:
        flash("Customer not found.", "danger")
        return redirect(url_for('customers.index'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        phone = request.form.get('phone', '').strip()
        city = request.form.get('city', '').strip()

        if not name:
            flash("Customer name is required.", "danger")
        else:
            try:
                customer_service.update_customer(customer_id, name, phone, city, changed_by=session.get('username', 'manager'))
                flash(f"Customer #{customer_id} updated successfully!", "success")
                return redirect(url_for('customers.index'))
            except Exception as e:
                logger.error(f"Error updating customer #{customer_id}: {e}")
                flash(f"Failed to update customer: {str(e)}", "danger")

    return render_template('customers/form.html', action='Edit', customer=customer)

@customers_bp.route('/customers/<int:customer_id>/orders')
@login_required
def order_history(customer_id: int):
    user_role = session.get('role', 'clerk')
    customer = customer_service.get_customer_by_id(customer_id, role=user_role)
    if not customer:
        flash("Customer not found.", "danger")
        return redirect(url_for('customers.index'))

    orders = customer_service.get_customer_order_history(customer_id, role=user_role)
    total_spent = sum(float(o['total_amount']) for o in orders if o.get('status') != 'Cancelled')

    return render_template(
        'customers/history.html',
        customer=customer,
        orders=orders,
        total_spent=total_spent
    )
