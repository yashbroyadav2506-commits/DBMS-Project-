"""
Orders blueprint handling order listings, atomic transactions, bill printing, PDF downloads, and cancellations.
"""
import io
import csv
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, Response, send_file
import mysql.connector
from auth import login_required, role_required
from services import order_service, product_service, customer_service
from services.pdf_service import generate_order_invoice_pdf
from logger import logger

orders_bp = Blueprint('orders', __name__)

@orders_bp.route('/orders')
@login_required
def index():
    user_role = session.get('role', 'clerk')

    search_query = request.args.get('q', '').strip()
    customer_id = request.args.get('customer_id', type=int)
    date_from = request.args.get('date_from', '').strip()
    date_to = request.args.get('date_to', '').strip()
    payment_mode = request.args.get('payment_mode', '').strip()
    status = request.args.get('status', '').strip()
    page = request.args.get('page', 1, type=int)

    orders, total_count, total_pages = order_service.get_orders(
        search_query=search_query,
        customer_id=customer_id,
        date_from=date_from,
        date_to=date_to,
        payment_mode=payment_mode,
        status=status,
        page=page,
        per_page=20,
        role=user_role
    )

    customers = customer_service.get_customers(role=user_role)

    return render_template(
        'orders/list.html',
        orders=orders,
        customers=customers,
        search_query=search_query,
        customer_id=customer_id,
        date_from=date_from,
        date_to=date_to,
        payment_mode=payment_mode,
        status=status,
        page=page,
        total_pages=total_pages,
        total_count=total_count
    )

@orders_bp.route('/orders/<int:order_id>')
@login_required
def detail(order_id: int):
    user_role = session.get('role', 'clerk')
    order_data = order_service.get_order_detail(order_id, role=user_role)
    if not order_data:
        flash("Order not found.", "danger")
        return redirect(url_for('orders.index'))

    return render_template(
        'orders/detail.html',
        order=order_data['order'],
        items=order_data['items'],
        total_amount=order_data['total_amount'],
        total_quantity=order_data['total_quantity']
    )

@orders_bp.route('/orders/<int:order_id>/pdf')
@login_required
def download_pdf(order_id: int):
    """
    Generates and returns the invoice PDF for download.
    """
    user_role = session.get('role', 'clerk')
    order_data = order_service.get_order_detail(order_id, role=user_role)
    if not order_data:
        flash("Order not found.", "danger")
        return redirect(url_for('orders.index'))

    pdf_buffer = generate_order_invoice_pdf(order_data)
    return send_file(
        pdf_buffer,
        as_attachment=True,
        download_name=f"Invoice_Order_{order_id}.pdf",
        mimetype='application/pdf'
    )

@orders_bp.route('/orders/place', methods=['GET', 'POST'])
@login_required
def place():
    user_role = session.get('role', 'clerk')

    if request.method == 'POST':
        customer_option = request.form.get('customer_option', 'existing')
        existing_customer_id = request.form.get('customer_id')
        new_name = request.form.get('new_customer_name', '').strip()
        new_phone = request.form.get('new_customer_phone', '').strip()
        new_city = request.form.get('new_customer_city', '').strip()
        payment_mode = request.form.get('payment_mode', 'UPI').strip()

        product_ids = request.form.getlist('product_id[]')
        quantities = request.form.getlist('quantity[]')

        items_to_order = []
        for pid, qty in zip(product_ids, quantities):
            if pid and qty:
                try:
                    p_val = int(pid)
                    q_val = int(qty)
                    if q_val > 0:
                        items_to_order.append((p_val, q_val))
                except ValueError:
                    pass

        if not items_to_order:
            flash("Please add at least one valid product item with quantity > 0.", "danger")
        else:
            try:
                # 1. Resolve customer
                if customer_option == 'new':
                    if not new_name:
                        flash("Customer Name is required when adding a new customer.", "danger")
                        customers = customer_service.get_customers(role=user_role)
                        products, _, _ = product_service.get_products(page=1, per_page=500, role=user_role)
                        return render_template('orders/place.html', customers=customers, products=products)
                    resolved_customer_id = customer_service.add_customer(new_name, new_phone, new_city, changed_by=session.get('username', 'user'))
                else:
                    if not existing_customer_id:
                        flash("Please select an existing customer.", "danger")
                        customers = customer_service.get_customers(role=user_role)
                        products, _, _ = product_service.get_products(page=1, per_page=500, role=user_role)
                        return render_template('orders/place.html', customers=customers, products=products)
                    resolved_customer_id = int(existing_customer_id)

                # 2. Place order inside transaction (triggers handle stock decrement and trigger validation)
                order_id = order_service.place_order(
                    customer_id=resolved_customer_id,
                    payment_mode=payment_mode,
                    items=items_to_order,
                    created_by=session.get('username', 'user')
                )

                flash(f"Order #{order_id} placed successfully! Inventory updated.", "success")
                return redirect(url_for('orders.detail', order_id=order_id))

            except mysql.connector.Error as err:
                logger.error(f"MySQL error placing order: {err}")
                if "Insufficient stock" in str(err) or err.sqlstate == '45000':
                    flash("Order Placement Failed & Rolled Back: Insufficient stock for one or more requested products.", "danger")
                else:
                    flash(f"Database error during order creation: {err.msg}", "danger")
            except Exception as e:
                logger.error(f"Error placing order: {e}")
                flash(f"Order creation failed: {str(e)}", "danger")

    customers = customer_service.get_customers(role=user_role)
    products, _, _ = product_service.get_products(page=1, per_page=500, role=user_role)

    return render_template('orders/place.html', customers=customers, products=products)

@orders_bp.route('/orders/<int:order_id>/cancel', methods=['POST'])
@login_required
@role_required('manager')
def cancel(order_id: int):
    try:
        order_service.cancel_order(order_id, cancelled_by=session.get('username', 'manager'))
        flash(f"Order #{order_id} has been Cancelled! Stock quantities were automatically restored via sp_cancel_order.", "success")
    except Exception as e:
        logger.error(f"Error cancelling order #{order_id}: {e}")
        flash(f"Failed to cancel order: {str(e)}", "danger")
    return redirect(url_for('orders.detail', order_id=order_id))

@orders_bp.route('/orders/export-csv')
@login_required
def export_csv():
    """
    Exports orders list to CSV.
    """
    user_role = session.get('role', 'clerk')
    orders, _, _ = order_service.get_orders(page=1, per_page=1000, role=user_role)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Order ID', 'Customer Name', 'Customer Phone', 'Order Date', 'Payment Mode', 'Status', 'Total Items', 'Total Amount (INR)'])

    for o in orders:
        writer.writerow([
            o['order_id'], o['customer_name'], o.get('customer_phone') or 'N/A',
            o['order_date'], o['payment_mode'], o.get('status', 'Completed'),
            o['total_items'], f"{float(o['total_amount']):.2f}"
        ])

    response = Response(output.getvalue(), mimetype='text/csv')
    response.headers['Content-Disposition'] = 'attachment; filename=orders_report.csv'
    return response
