"""
Suppliers and Brands blueprint for manager-only supplier and brand management.
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from auth import login_required, role_required
from services import supplier_brand_service
from logger import logger

suppliers_brands_bp = Blueprint('suppliers_brands', __name__)

# --- Suppliers ---

@suppliers_brands_bp.route('/suppliers')
@login_required
@role_required('manager')
def suppliers_list():
    suppliers = supplier_brand_service.get_all_suppliers(role='manager')
    return render_template('suppliers_brands/suppliers_list.html', suppliers=suppliers)

@suppliers_brands_bp.route('/suppliers/add', methods=['GET', 'POST'])
@login_required
@role_required('manager')
def add_supplier():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        phone = request.form.get('phone', '').strip()
        email = request.form.get('email', '').strip()

        if not name:
            flash("Supplier name is required.", "danger")
        else:
            try:
                sid = supplier_brand_service.add_supplier(name, phone, email, changed_by=session.get('username', 'manager'))
                flash(f"Supplier '{name}' added successfully (ID #{sid})!", "success")
                return redirect(url_for('suppliers_brands.suppliers_list'))
            except Exception as e:
                logger.error(f"Error adding supplier: {e}")
                flash(f"Failed to add supplier: {str(e)}", "danger")

    return render_template('suppliers_brands/supplier_form.html', action='Add', supplier=None)

@suppliers_brands_bp.route('/suppliers/edit/<int:supplier_id>', methods=['GET', 'POST'])
@login_required
@role_required('manager')
def edit_supplier(supplier_id: int):
    supplier = supplier_brand_service.get_supplier_by_id(supplier_id)
    if not supplier:
        flash("Supplier not found.", "danger")
        return redirect(url_for('suppliers_brands.suppliers_list'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        phone = request.form.get('phone', '').strip()
        email = request.form.get('email', '').strip()

        if not name:
            flash("Supplier name is required.", "danger")
        else:
            try:
                supplier_brand_service.update_supplier(supplier_id, name, phone, email, changed_by=session.get('username', 'manager'))
                flash(f"Supplier #{supplier_id} updated successfully!", "success")
                return redirect(url_for('suppliers_brands.suppliers_list'))
            except Exception as e:
                logger.error(f"Error updating supplier #{supplier_id}: {e}")
                flash(f"Failed to update supplier: {str(e)}", "danger")

    return render_template('suppliers_brands/supplier_form.html', action='Edit', supplier=supplier)

@suppliers_brands_bp.route('/suppliers/delete/<int:supplier_id>', methods=['POST'])
@login_required
@role_required('manager')
def delete_supplier(supplier_id: int):
    try:
        supplier_brand_service.delete_supplier(supplier_id, changed_by=session.get('username', 'manager'))
        flash(f"Supplier #{supplier_id} deleted successfully.", "success")
    except ValueError as val_err:
        flash(str(val_err), "warning")
    except Exception as e:
        logger.error(f"Error deleting supplier #{supplier_id}: {e}")
        flash(f"Failed to delete supplier: {str(e)}", "danger")
    return redirect(url_for('suppliers_brands.suppliers_list'))

# --- Brands ---

@suppliers_brands_bp.route('/brands')
@login_required
@role_required('manager')
def brands_list():
    brands = supplier_brand_service.get_all_brands(role='manager')
    return render_template('suppliers_brands/brands_list.html', brands=brands)

@suppliers_brands_bp.route('/brands/add', methods=['GET', 'POST'])
@login_required
@role_required('manager')
def add_brand():
    if request.method == 'POST':
        brand_name = request.form.get('brand_name', '').strip()
        if not brand_name:
            flash("Brand name is required.", "danger")
        else:
            try:
                bid = supplier_brand_service.add_brand(brand_name, changed_by=session.get('username', 'manager'))
                flash(f"Brand '{brand_name}' added successfully (ID #{bid})!", "success")
                return redirect(url_for('suppliers_brands.brands_list'))
            except Exception as e:
                logger.error(f"Error adding brand: {e}")
                flash(f"Failed to add brand: {str(e)}", "danger")

    return render_template('suppliers_brands/brand_form.html', action='Add', brand=None)

@suppliers_brands_bp.route('/brands/edit/<int:brand_id>', methods=['GET', 'POST'])
@login_required
@role_required('manager')
def edit_brand(brand_id: int):
    brand = supplier_brand_service.get_brand_by_id(brand_id)
    if not brand:
        flash("Brand not found.", "danger")
        return redirect(url_for('suppliers_brands.brands_list'))

    if request.method == 'POST':
        brand_name = request.form.get('brand_name', '').strip()
        if not brand_name:
            flash("Brand name is required.", "danger")
        else:
            try:
                supplier_brand_service.update_brand(brand_id, brand_name, changed_by=session.get('username', 'manager'))
                flash(f"Brand #{brand_id} updated successfully!", "success")
                return redirect(url_for('suppliers_brands.brands_list'))
            except Exception as e:
                logger.error(f"Error updating brand #{brand_id}: {e}")
                flash(f"Failed to update brand: {str(e)}", "danger")

    return render_template('suppliers_brands/brand_form.html', action='Edit', brand=brand)

@suppliers_brands_bp.route('/brands/delete/<int:brand_id>', methods=['POST'])
@login_required
@role_required('manager')
def delete_brand(brand_id: int):
    try:
        supplier_brand_service.delete_brand(brand_id, changed_by=session.get('username', 'manager'))
        flash(f"Brand #{brand_id} deleted successfully.", "success")
    except ValueError as val_err:
        flash(str(val_err), "warning")
    except Exception as e:
        logger.error(f"Error deleting brand #{brand_id}: {e}")
        flash(f"Failed to delete brand: {str(e)}", "danger")
    return redirect(url_for('suppliers_brands.brands_list'))
