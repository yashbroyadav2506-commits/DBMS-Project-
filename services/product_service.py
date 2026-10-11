"""
Product service module handling catalog queries, inventory updates, and procedure calls.
"""
from typing import List, Dict, Any, Optional, Tuple
import mysql.connector
from db import get_db_cursor
from services.admin_service import log_audit
from logger import logger

def get_products(
    search_query: str = '',
    category_filter: str = '',
    brand_filter: str = '',
    stock_status: str = '',
    include_inactive: bool = False,
    sort_by: str = 'product_id',
    sort_order: str = 'ASC',
    page: int = 1,
    per_page: int = 20,
    role: str = 'clerk'
) -> Tuple[List[Dict[str, Any]], int, int]:
    """
    Retrieves paginated products with filtering and sorting.
    Returns (products_list, total_count, total_pages).
    """
    allowed_sort_fields = {
        'product_id': 'p.product_id',
        'product_name': 'p.product_name',
        'price': 'p.price',
        'stock_qty': 'p.stock_qty',
        'category': 'p.category',
        'brand': 'b.brand_name',
        'supplier': 's.name'
    }
    sort_column = allowed_sort_fields.get(sort_by, 'p.product_id')
    sort_direction = 'DESC' if sort_order.upper() == 'DESC' else 'ASC'

    where_clauses = ["1=1"]
    params = []

    if not include_inactive:
        where_clauses.append("p.is_active = 1")

    if search_query:
        where_clauses.append("(p.product_name LIKE %s OR p.category LIKE %s OR b.brand_name LIKE %s OR s.name LIKE %s)")
        like_term = f"%{search_query}%"
        params.extend([like_term, like_term, like_term, like_term])

    if category_filter:
        where_clauses.append("p.category = %s")
        params.append(category_filter)

    if brand_filter:
        where_clauses.append("b.brand_name = %s")
        params.append(brand_filter)

    if stock_status == 'low':
        where_clauses.append("p.stock_qty <= p.reorder_level")
    elif stock_status == 'out':
        where_clauses.append("p.stock_qty = 0")
    elif stock_status == 'ok':
        where_clauses.append("p.stock_qty > p.reorder_level")

    where_sql = " AND ".join(where_clauses)

    count_sql = f"""
        SELECT COUNT(*) AS total
        FROM product p
        LEFT JOIN brand b ON p.brand_id = b.brand_id
        LEFT JOIN supplier s ON p.supplier_id = s.supplier_id
        WHERE {where_sql};
    """

    select_sql = f"""
        SELECT p.product_id, p.product_name, p.category, p.price, p.stock_qty, p.reorder_level,
               p.is_active,
               IFNULL(b.brand_name, 'No Brand') AS brand,
               IFNULL(s.name, 'No Supplier') AS supplier
        FROM product p
        LEFT JOIN brand b ON p.brand_id = b.brand_id
        LEFT JOIN supplier s ON p.supplier_id = s.supplier_id
        WHERE {where_sql}
        ORDER BY {sort_column} {sort_direction}
        LIMIT %s OFFSET %s;
    """

    def execute_fetch(query_role):
        with get_db_cursor(query_role) as (conn, cursor):
            cursor.execute(count_sql, tuple(params))
            total_count = cursor.fetchone()['total']

            total_pages = max(1, (total_count + per_page - 1) // per_page)
            active_page = max(1, min(page, total_pages))
            offset = (active_page - 1) * per_page

            query_params = list(params)
            query_params.extend([per_page, offset])
            cursor.execute(select_sql, tuple(query_params))
            products = cursor.fetchall()
            return products, total_count, total_pages

    try:
        return execute_fetch(role)
    except mysql.connector.Error as err:
        if err.errno == 1142:  # Permission denied on brand/supplier join for clerk
            return execute_fetch('manager')
        raise err

def get_product_by_id(product_id: int, role: str = 'clerk') -> Optional[Dict[str, Any]]:
    """
    Fetches a single product by ID.
    """
    sql = """
        SELECT p.product_id, p.product_name, p.price, p.category, p.brand_id, p.supplier_id,
               p.stock_qty, p.reorder_level, p.is_active,
               IFNULL(b.brand_name, 'No Brand') AS brand,
               IFNULL(s.name, 'No Supplier') AS supplier
        FROM product p
        LEFT JOIN brand b ON p.brand_id = b.brand_id
        LEFT JOIN supplier s ON p.supplier_id = s.supplier_id
        WHERE p.product_id = %s;
    """
    try:
        with get_db_cursor(role) as (conn, cursor):
            cursor.execute(sql, (product_id,))
            return cursor.fetchone()
    except mysql.connector.Error as err:
        if err.errno == 1142:
            with get_db_cursor('manager') as (conn, cursor):
                cursor.execute(sql, (product_id,))
                return cursor.fetchone()
        raise err

def add_product(data: Dict[str, Any], changed_by: str = 'manager') -> int:
    """
    Inserts a new product into the database and logs to audit_log.
    """
    with get_db_cursor('manager', commit=True) as (conn, cursor):
        sql = """
            INSERT INTO product (product_name, price, category, brand_id, supplier_id, stock_qty, reorder_level, is_active)
            VALUES (%s, %s, %s, %s, %s, %s, %s, 1);
        """
        cursor.execute(sql, (
            data['product_name'],
            data['price'],
            data.get('category'),
            data.get('brand_id'),
            data.get('supplier_id'),
            data.get('stock_qty', 0),
            data.get('reorder_level', 10)
        ))
        product_id = cursor.lastrowid

    log_audit('product', 'INSERT', product_id, None,
              f"name: {data['product_name']}, price: {data['price']}, stock: {data.get('stock_qty', 0)}",
              changed_by)
    return product_id

def update_product(product_id: int, data: Dict[str, Any], changed_by: str = 'manager'):
    """
    Updates an existing product and logs to audit_log.
    """
    old_prod = get_product_by_id(product_id, role='manager')
    if not old_prod:
        raise ValueError("Product not found")

    with get_db_cursor('manager', commit=True) as (conn, cursor):
        sql = """
            UPDATE product
            SET product_name = %s, price = %s, category = %s, brand_id = %s,
                supplier_id = %s, stock_qty = %s, reorder_level = %s
            WHERE product_id = %s;
        """
        cursor.execute(sql, (
            data['product_name'],
            data['price'],
            data.get('category'),
            data.get('brand_id'),
            data.get('supplier_id'),
            data.get('stock_qty', 0),
            data.get('reorder_level', 10),
            product_id
        ))

    old_desc = f"name: {old_prod['product_name']}, price: {old_prod['price']}, stock: {old_prod['stock_qty']}"
    new_desc = f"name: {data['product_name']}, price: {data['price']}, stock: {data.get('stock_qty', 0)}"
    log_audit('product', 'UPDATE', product_id, old_desc, new_desc, changed_by)

def soft_delete_product(product_id: int, changed_by: str = 'manager'):
    """
    Soft-deletes a product by marking is_active = 0.
    """
    with get_db_cursor('manager', commit=True) as (conn, cursor):
        cursor.execute("UPDATE product SET is_active = 0 WHERE product_id = %s;", (product_id,))
    log_audit('product', 'SOFT_DELETE', product_id, "is_active: 1", "is_active: 0", changed_by)

def restore_product(product_id: int, changed_by: str = 'manager'):
    """
    Restores a soft-deleted product by marking is_active = 1.
    """
    with get_db_cursor('manager', commit=True) as (conn, cursor):
        cursor.execute("UPDATE product SET is_active = 1 WHERE product_id = %s;", (product_id,))
    log_audit('product', 'RESTORE', product_id, "is_active: 0", "is_active: 1", changed_by)

def hard_delete_product(product_id: int, changed_by: str = 'manager'):
    """
    Hard-deletes a product, catching foreign key constraint errors gracefully.
    """
    old_prod = get_product_by_id(product_id, role='manager')
    try:
        with get_db_cursor('manager', commit=True) as (conn, cursor):
            cursor.execute("DELETE FROM product WHERE product_id = %s;", (product_id,))
        if old_prod:
            log_audit('product', 'HARD_DELETE', product_id, f"name: {old_prod['product_name']}", None, changed_by)
    except mysql.connector.Error as err:
        if err.errno == 1451:
            raise ValueError(f"Cannot delete Product #{product_id} permanently because it appears in existing customer orders. Consider soft-deleting it instead.")
        raise err

def restock_product(product_id: int, quantity: int, changed_by: str = 'manager'):
    """
    Calls stored procedure sp_restock_product to increment stock, and records in audit log.
    """
    with get_db_cursor('manager', commit=True) as (conn, cursor):
        cursor.callproc('sp_restock_product', (product_id, quantity))

    log_audit('product', 'RESTOCK', product_id, None, f"+{quantity} units via sp_restock_product", changed_by)

def get_low_stock_products() -> List[Dict[str, Any]]:
    """
    Queries low stock products with supplier and brand info.
    """
    with get_db_cursor('manager') as (conn, cursor):
        sql = """
            SELECT p.product_id, p.product_name, p.stock_qty, p.reorder_level, p.price, p.category,
                   IFNULL(s.name, 'No Supplier') AS supplier_name,
                   IFNULL(s.phone, 'N/A') AS supplier_phone,
                   IFNULL(b.brand_name, 'No Brand') AS brand_name
            FROM product p
            LEFT JOIN supplier s ON p.supplier_id = s.supplier_id
            LEFT JOIN brand b ON p.brand_id = b.brand_id
            WHERE p.stock_qty <= p.reorder_level AND p.is_active = 1
            ORDER BY p.stock_qty ASC;
        """
        cursor.execute(sql)
        return cursor.fetchall()

def get_supplier_restock_suggestions() -> List[Dict[str, Any]]:
    """
    Groups low stock products by supplier and calculates suggested order quantities.
    """
    with get_db_cursor('manager') as (conn, cursor):
        sql = """
            SELECT 
                IFNULL(s.name, 'Unassigned Supplier') AS supplier_name,
                IFNULL(s.phone, 'N/A') AS supplier_phone,
                IFNULL(s.email, 'N/A') AS supplier_email,
                p.product_id,
                p.product_name,
                p.category,
                p.stock_qty,
                p.reorder_level,
                p.price,
                GREATEST((p.reorder_level * 2) - p.stock_qty, 10) AS suggested_qty,
                (GREATEST((p.reorder_level * 2) - p.stock_qty, 10) * p.price) AS estimated_cost
            FROM product p
            LEFT JOIN supplier s ON p.supplier_id = s.supplier_id
            WHERE p.stock_qty <= p.reorder_level AND p.is_active = 1
            ORDER BY s.name ASC, p.stock_qty ASC;
        """
        cursor.execute(sql)
        return cursor.fetchall()

def get_categories(role: str = 'clerk') -> List[str]:
    """
    Fetches distinct categories.
    """
    try:
        with get_db_cursor(role) as (conn, cursor):
            cursor.execute("SELECT DISTINCT category FROM product WHERE category IS NOT NULL AND is_active = 1 ORDER BY category;")
            return [r['category'] for r in cursor.fetchall()]
    except mysql.connector.Error:
        with get_db_cursor('manager') as (conn, cursor):
            cursor.execute("SELECT DISTINCT category FROM product WHERE category IS NOT NULL AND is_active = 1 ORDER BY category;")
            return [r['category'] for r in cursor.fetchall()]

def get_brands(role: str = 'clerk') -> List[Dict[str, Any]]:
    """
    Fetches all brands with manager fallback for permission.
    """
    try:
        with get_db_cursor(role) as (conn, cursor):
            cursor.execute("SELECT brand_id, brand_name FROM brand ORDER BY brand_name;")
            return cursor.fetchall()
    except mysql.connector.Error:
        with get_db_cursor('manager') as (conn, cursor):
            cursor.execute("SELECT brand_id, brand_name FROM brand ORDER BY brand_name;")
            return cursor.fetchall()

def get_suppliers(role: str = 'clerk') -> List[Dict[str, Any]]:
    """
    Fetches all suppliers with manager fallback for permission.
    """
    try:
        with get_db_cursor(role) as (conn, cursor):
            cursor.execute("SELECT supplier_id, name, phone, email FROM supplier ORDER BY name;")
            return cursor.fetchall()
    except mysql.connector.Error:
        with get_db_cursor('manager') as (conn, cursor):
            cursor.execute("SELECT supplier_id, name, phone, email FROM supplier ORDER BY name;")
            return cursor.fetchall()
