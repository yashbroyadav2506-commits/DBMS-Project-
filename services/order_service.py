"""
Order service module handling transactional order placement, cancellation, item lookups, and bill generation.
"""
from typing import List, Dict, Any, Optional, Tuple
import mysql.connector
from db import get_db_cursor
from services.admin_service import log_audit
from logger import logger

def get_orders(
    search_query: str = '',
    customer_id: Optional[int] = None,
    date_from: str = '',
    date_to: str = '',
    payment_mode: str = '',
    status: str = '',
    page: int = 1,
    per_page: int = 20,
    role: str = 'clerk'
) -> Tuple[List[Dict[str, Any]], int, int]:
    """
    Retrieves filtered and paginated orders list.
    Returns (orders_list, total_count, total_pages).
    """
    where_clauses = ["1=1"]
    params = []

    if search_query:
        where_clauses.append("(c.name LIKE %s OR o.order_id = %s)")
        params.extend([f"%{search_query}%", search_query if search_query.isdigit() else -1])

    if customer_id:
        where_clauses.append("o.customer_id = %s")
        params.append(customer_id)

    if date_from:
        where_clauses.append("o.order_date >= %s")
        params.append(date_from)

    if date_to:
        where_clauses.append("o.order_date <= %s")
        params.append(date_to)

    if payment_mode:
        where_clauses.append("o.payment_mode = %s")
        params.append(payment_mode)

    if status:
        where_clauses.append("o.status = %s")
        params.append(status)

    where_sql = " AND ".join(where_clauses)

    with get_db_cursor(role) as (conn, cursor):
        count_sql = f"""
            SELECT COUNT(DISTINCT o.order_id) AS total
            FROM orders o
            JOIN customer c ON o.customer_id = c.customer_id
            WHERE {where_sql};
        """
        cursor.execute(count_sql, tuple(params))
        total_count = cursor.fetchone()['total']

        total_pages = max(1, (total_count + per_page - 1) // per_page)
        page = max(1, min(page, total_pages))
        offset = (page - 1) * per_page

        select_sql = f"""
            SELECT o.order_id, c.customer_id, c.name AS customer_name, c.phone AS customer_phone,
                   o.order_date, o.payment_mode, o.status,
                   IFNULL(SUM(oi.quantity * oi.unit_price), 0) AS total_amount,
                   COUNT(oi.order_item_id) AS total_items
            FROM orders o
            JOIN customer c ON o.customer_id = c.customer_id
            LEFT JOIN order_item oi ON o.order_id = oi.order_id
            WHERE {where_sql}
            GROUP BY o.order_id, c.customer_id, c.name, c.phone, o.order_date, o.payment_mode, o.status
            ORDER BY o.order_id DESC
            LIMIT %s OFFSET %s;
        """
        query_params = list(params)
        query_params.extend([per_page, offset])
        cursor.execute(select_sql, tuple(query_params))
        orders = cursor.fetchall()

    return orders, total_count, total_pages

def get_order_detail(order_id: int, role: str = 'clerk') -> Optional[Dict[str, Any]]:
    """
    Fetches full order bill details including customer and items.
    """
    with get_db_cursor(role) as (conn, cursor):
        order_sql = """
            SELECT o.order_id, o.order_date, o.payment_mode, o.status,
                   c.customer_id, c.name AS customer_name, c.phone, c.city
            FROM orders o
            JOIN customer c ON o.customer_id = c.customer_id
            WHERE o.order_id = %s;
        """
        cursor.execute(order_sql, (order_id,))
        order = cursor.fetchone()
        if not order:
            return None

        items_sql = """
            SELECT oi.order_item_id, oi.product_id, p.product_name, p.category,
                   oi.quantity, oi.unit_price, (oi.quantity * oi.unit_price) AS line_total
            FROM order_item oi
            JOIN product p ON oi.product_id = p.product_id
            WHERE oi.order_id = %s
            ORDER BY oi.order_item_id ASC;
        """
        cursor.execute(items_sql, (order_id,))
        items = cursor.fetchall()

        total_amount = sum(float(item['line_total']) for item in items)
        total_quantity = sum(int(item['quantity']) for item in items)

        return {
            'order': order,
            'items': items,
            'total_amount': total_amount,
            'total_quantity': total_quantity
        }

def place_order(
    customer_id: int,
    payment_mode: str,
    items: List[Tuple[int, int]],
    created_by: str = 'system'
) -> int:
    """
    Places an order atomically inside a transaction.
    - Prevents N+1 by batch-fetching product prices.
    - Inserts order header.
    - Inserts items (firing trg_check_stock and trg_reduce_stock triggers).
    - Commits transaction or rolls back on any error (such as insufficient stock).
    - Logs to audit_log.
    """
    if not items:
        raise ValueError("Cannot place an order with zero items.")

    # 1. Batch fetch prices to avoid N+1 query problem
    product_ids = [pid for pid, _ in items]
    placeholders = ", ".join(["%s"] * len(product_ids))
    with get_db_cursor('manager') as (conn, cursor):
        cursor.execute(f"SELECT product_id, product_name, price, stock_qty FROM product WHERE product_id IN ({placeholders});", tuple(product_ids))
        prod_map = {row['product_id']: row for row in cursor.fetchall()}

    for pid, qty in items:
        if pid not in prod_map:
            raise ValueError(f"Product #{pid} does not exist.")
        if qty <= 0:
            raise ValueError(f"Quantity for product #{pid} must be positive.")

    # 2. Transactional Write using manager connection pool
    with get_db_cursor('manager', commit=True) as (conn, cursor):
        # Insert Order header
        cursor.execute(
            "INSERT INTO orders (customer_id, order_date, payment_mode, status) VALUES (%s, CURDATE(), %s, 'Completed');",
            (customer_id, payment_mode)
        )
        order_id = cursor.lastrowid

        # Insert items (Triggers trg_check_stock will validate stock availability)
        for pid, qty in items:
            unit_price = prod_map[pid]['price']
            cursor.execute(
                "INSERT INTO order_item (order_id, product_id, quantity, unit_price) VALUES (%s, %s, %s, %s);",
                (order_id, pid, qty, unit_price)
            )

    log_audit('orders', 'PLACE_ORDER', order_id, None,
              f"customer_id: {customer_id}, items_count: {len(items)}, payment: {payment_mode}",
              created_by)
    return order_id

def cancel_order(order_id: int, cancelled_by: str = 'manager'):
    """
    Cancels an order by calling sp_cancel_order stored procedure.
    Restores inventory stock atomically and marks order status as Cancelled.
    """
    with get_db_cursor('manager', commit=True) as (conn, cursor):
        cursor.callproc('sp_cancel_order', (order_id, cancelled_by))
