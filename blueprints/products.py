"""
Products blueprint handling catalog listings, pagination, CRUD, soft-delete, restock, and CSV export.
"""
import io
import csv
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, Response
from auth import login_required, role_required
from services import product_service
from logger import logger

products_bp = Blueprint('products', __name__)

@products_bp.route('/products')
@login_required
def index():
    user_role = session.get('role', 'clerk')

    search_query = request.args.get('q', '').strip()
    category_filter = request.args.get('category', '').strip()
    brand_filter = request.args.get('brand', '').strip()
    stock_status = request.args.get('stock', '').strip()
    include_inactive = request.args.get('show_inactive', '0') == '1' and user_role == 'manager'
    sort_by = request.args.get('sort_by', 'product_id')
    sort_order = request.args.get('order', 'ASC')
    page = request.args.get('page', 1, type=int)

    products, total_count, total_pages = product_service.get_products(
        search_query=search_query,
        category_filter=category_filter,
        brand_filter=brand_filter,
        stock_status=stock_status,
        include_inactive=include_inactive,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        per_page=20,
        role=user_role
    )

    categories = product_service.get_categories(role=user_role)
    brands = product_service.get_brands(role=user_role)

    return render_template(
        'products/list.html',
        products=products,
        categories=categories,
        brands=brands,
        search_query=search_query,
        category_filter=category_filter,
        brand_filter=brand_filter,
        stock_status=stock_status,
        include_inactive=include_inactive,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        total_pages=total_pages,
        total_count=total_count
    )

@products_bp.route('/products/add', methods=['GET', 'POST'])
@login_required
@role_required('manager')
def add():
    brands = product_service.get_brands('manager')
    suppliers = product_service.get_suppliers('manager')
    categories = product_service.get_categories('manager')

    form_data = {}
    if request.method == 'POST':
        product_name = request.form.get('product_name', '').strip()
        category = request.form.get('category', '').strip()
        price = request.form.get('price', '').strip()
        stock_qty = request.form.get('stock_qty', '0').strip()
        reorder_level = request.form.get('reorder_level', '10').strip()
        brand_id = request.form.get('brand_id', '').strip() or None
        supplier_id = request.form.get('supplier_id', '').strip() or None

        form_data = {
            'product_name': product_name,
            'category': category,
            'price': price,
            'stock_qty': stock_qty,
            'reorder_level': reorder_level,
            'brand_id': int(brand_id) if brand_id else None,
            'supplier_id': int(supplier_id) if supplier_id else None
        }

        # Server-side validation
        if not product_name:
            flash("Product name is required.", "danger")
        elif not price:
            flash("Product price is required.", "danger")
        else:
            try:
                price_val = float(price)
                stock_val = int(stock_qty or 0)
                reorder_val = int(reorder_level or 10)

                if price_val <= 0:
                    flash("Price must be strictly positive (greater than 0).", "danger")
                elif stock_val < 0:
                    flash("Stock quantity cannot be negative.", "danger")
                elif reorder_val < 0:
                    flash("Reorder level cannot be negative.", "danger")
                else:
                    new_id = product_service.add_product({
                        'product_name': product_name,
                        'price': price_val,
                        'category': category,
                        'brand_id': int(brand_id) if brand_id else None,
                        'supplier_id': int(supplier_id) if supplier_id else None,
                        'stock_qty': stock_val,
                        'reorder_level': reorder_val
                    }, changed_by=session.get('username', 'manager'))
                    flash(f"Product '{product_name}' (ID #{new_id}) created successfully!", "success")
                    return redirect(url_for('products.index'))
            except ValueError:
                flash("Price and quantities must be valid numeric values.", "danger")
            except Exception as e:
                logger.error(f"Error adding product: {e}")
                flash(f"Failed to add product: {str(e)}", "danger")

    return render_template(
        'products/form.html',
        action='Add',
        brands=brands,
        suppliers=suppliers,
        categories=categories,
        product=form_data
    )

@products_bp.route('/products/edit/<int:product_id>', methods=['GET', 'POST'])
@login_required
@role_required('manager')
def edit(product_id: int):
    product = product_service.get_product_by_id(product_id, role='manager')
    if not product:
        flash("Product not found.", "danger")
        return redirect(url_for('products.index'))

    brands = product_service.get_brands('manager')
    suppliers = product_service.get_suppliers('manager')
    categories = product_service.get_categories('manager')

    if request.method == 'POST':
        product_name = request.form.get('product_name', '').strip()
        category = request.form.get('category', '').strip()
        price = request.form.get('price', '').strip()
        stock_qty = request.form.get('stock_qty', '').strip()
        reorder_level = request.form.get('reorder_level', '').strip()
        brand_id = request.form.get('brand_id', '').strip() or None
        supplier_id = request.form.get('supplier_id', '').strip() or None

        if not product_name or not price:
            flash("Product name and price are required fields.", "danger")
        else:
            try:
                price_val = float(price)
                stock_val = int(stock_qty or 0)
                reorder_val = int(reorder_level or 10)

                if price_val <= 0:
                    flash("Price must be strictly positive.", "danger")
                elif stock_val < 0:
                    flash("Stock quantity cannot be negative.", "danger")
                else:
                    product_service.update_product(product_id, {
                        'product_name': product_name,
                        'price': price_val,
                        'category': category,
                        'brand_id': int(brand_id) if brand_id else None,
                        'supplier_id': int(supplier_id) if supplier_id else None,
                        'stock_qty': stock_val,
                        'reorder_level': reorder_val
                    }, changed_by=session.get('username', 'manager'))
                    flash(f"Product #{product_id} updated successfully!", "success")
                    return redirect(url_for('products.index'))
            except ValueError:
                flash("Invalid numeric value for price or stock quantity.", "danger")
            except Exception as e:
                logger.error(f"Error editing product #{product_id}: {e}")
                flash(f"Failed to update product: {str(e)}", "danger")

    return render_template(
        'products/form.html',
        action='Edit',
        brands=brands,
        suppliers=suppliers,
        categories=categories,
        product=product
    )

@products_bp.route('/products/soft-delete/<int:product_id>', methods=['POST'])
@login_required
@role_required('manager')
def soft_delete(product_id: int):
    try:
        product_service.soft_delete_product(product_id, changed_by=session.get('username', 'manager'))
        flash(f"Product #{product_id} soft-deleted. It is now hidden from the store catalog but preserved in orders.", "info")
    except Exception as e:
        logger.error(f"Error soft deleting product #{product_id}: {e}")
        flash(f"Failed to soft delete product: {e}", "danger")
    return redirect(url_for('products.index'))

@products_bp.route('/products/restore/<int:product_id>', methods=['POST'])
@login_required
@role_required('manager')
def restore(product_id: int):
    try:
        product_service.restore_product(product_id, changed_by=session.get('username', 'manager'))
        flash(f"Product #{product_id} restored to active catalog!", "success")
    except Exception as e:
        logger.error(f"Error restoring product #{product_id}: {e}")
        flash(f"Failed to restore product: {e}", "danger")
    return redirect(url_for('products.index', show_inactive='1'))

@products_bp.route('/products/delete/<int:product_id>', methods=['POST'])
@login_required
@role_required('manager')
def delete(product_id: int):
    try:
        product_service.hard_delete_product(product_id, changed_by=session.get('username', 'manager'))
        flash(f"Product #{product_id} permanently deleted from database.", "success")
    except ValueError as val_err:
        flash(str(val_err), "warning")
    except Exception as e:
        logger.error(f"Error permanently deleting product #{product_id}: {e}")
        flash(f"Database error during deletion: {e}", "danger")
    return redirect(url_for('products.index'))

@products_bp.route('/products/restock', methods=['GET', 'POST'])
@login_required
@role_required('manager')
def restock():
    if request.method == 'POST':
        product_id = request.form.get('product_id', '').strip()
        quantity = request.form.get('quantity', '').strip()

        if not product_id or not quantity:
            flash("Please choose a product and enter quantity.", "danger")
        else:
            try:
                pid = int(product_id)
                qty = int(quantity)
                if qty <= 0:
                    flash("Restock quantity must be a positive integer.", "danger")
                else:
                    product_service.restock_product(pid, qty, changed_by=session.get('username', 'manager'))
                    flash(f"Successfully restocked Product #{pid} with +{qty} units via Stored Procedure sp_restock_product!", "success")
                    return redirect(url_for('products.index'))
            except ValueError:
                flash("Quantity must be a valid number.", "danger")
            except Exception as e:
                logger.error(f"Stored procedure error during restock: {e}")
                flash(f"Restock procedure failed: {str(e)}", "danger")

    # Fetch products for restock dropdown
    products, _, _ = product_service.get_products(page=1, per_page=500, role='manager')
    selected_pid = request.args.get('product_id', type=int)

    return render_template('products/restock.html', products=products, selected_pid=selected_pid)

@products_bp.route('/products/restock-list')
@login_required
@role_required('manager')
def restock_list():
    """
    Manager restock list showing suggested reorder quantities grouped by supplier.
    """
    suggestions = product_service.get_supplier_restock_suggestions()
    total_estimated_cost = sum(float(item['estimated_cost']) for item in suggestions)
    return render_template(
        'products/restock_list.html',
        suggestions=suggestions,
        total_estimated_cost=total_estimated_cost
    )

@products_bp.route('/products/export-csv')
@login_required
def export_csv():
    """
    Exports product catalog to CSV file.
    """
    products, _, _ = product_service.get_products(page=1, per_page=1000, role='clerk')
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Product ID', 'Product Name', 'Category', 'Price (INR)', 'Stock Qty', 'Reorder Level', 'Brand', 'Supplier', 'Status'])

    for p in products:
        status = 'Active' if p.get('is_active', 1) else 'Inactive'
        writer.writerow([
            p['product_id'], p['product_name'], p.get('category') or 'N/A',
            f"{p['price']:.2f}", p['stock_qty'], p['reorder_level'],
            p.get('brand') or 'N/A', p.get('supplier') or 'N/A', status
        ])

    response = Response(output.getvalue(), mimetype='text/csv')
    response.headers['Content-Disposition'] = 'attachment; filename=products_catalog.csv'
    return response
