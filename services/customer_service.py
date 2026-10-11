"""
Customer service module for customer CRUD operations and customer order history.
"""
from typing import List, Dict, Any, Optional
from db import get_db_cursor
from services.admin_service import log_audit

def get_customers(search_query: str = '', role: str = 'clerk') -> List[Dict[str, Any]]:
    """
    Fetches all customers with optional search by name, phone, or city.
    """
    with get_db_cursor(role) as (conn, cursor):
        sql = """
            SELECT c.customer_id, c.name, c.phone, c.city,
                   COUNT(o.order_id) AS total_orders,
                   IFNULL(SUM(oi.quantity * oi.unit_price), 0) AS total_spent
            FROM customer c
            LEFT JOIN orders o ON c.customer_id = o.customer_id AND o.status != 'Cancelled'
            LEFT JOIN order_item oi ON o.order_id = oi.order_id
            WHERE 1=1
        """
        params = []
        if search_query:
            sql += " AND (c.name LIKE %s OR c.phone LIKE %s OR c.city LIKE %s)"
            term = f"%{search_query}%"
            params.extend([term, term, term])

        sql += " GROUP BY c.customer_id, c.name, c.phone, c.city ORDER BY c.name ASC;"
        cursor.execute(sql, tuple(params))
        return cursor.fetchall()

def get_customer_by_id(customer_id: int, role: str = 'clerk') -> Optional[Dict[str, Any]]:
    """
    Fetches customer by ID.
    """
    with get_db_cursor(role) as (conn, cursor):
        cursor.execute("SELECT customer_id, name, phone, city FROM customer WHERE customer_id = %s;", (customer_id,))
        return cursor.fetchone()

def add_customer(name: str, phone: str, city: str, changed_by: str = 'system') -> int:
    """
    Adds a new customer and logs to audit_log.
    """
    with get_db_cursor('manager', commit=True) as (conn, cursor):
        cursor.execute(
            "INSERT INTO customer (name, phone, city) VALUES (%s, %s, %s);",
            (name.strip(), phone.strip() or None, city.strip() or None)
        )
        customer_id = cursor.lastrowid

    log_audit('customer', 'INSERT', customer_id, None, f"name: {name}, phone: {phone}, city: {city}", changed_by)
    return customer_id

def update_customer(customer_id: int, name: str, phone: str, city: str, changed_by: str = 'system'):
    """
    Updates an existing customer.
    """
    old = get_customer_by_id(customer_id, role='manager')
    with get_db_cursor('manager', commit=True) as (conn, cursor):
        cursor.execute(
            "UPDATE customer SET name = %s, phone = %s, city = %s WHERE customer_id = %s;",
            (name.strip(), phone.strip() or None, city.strip() or None, customer_id)
        )

    old_desc = f"name: {old['name']}, phone: {old['phone']}, city: {old['city']}" if old else ""
    new_desc = f"name: {name}, phone: {phone}, city: {city}"
    log_audit('customer', 'UPDATE', customer_id, old_desc, new_desc, changed_by)

def get_customer_order_history(customer_id: int, role: str = 'clerk') -> List[Dict[str, Any]]:
    """
    Fetches all orders placed by a specific customer.
    """
    with get_db_cursor(role) as (conn, cursor):
        sql = """
            SELECT o.order_id, o.order_date, o.payment_mode, o.status,
                   IFNULL(SUM(oi.quantity * oi.unit_price), 0) AS total_amount,
                   COUNT(oi.order_item_id) AS total_items
            FROM orders o
            LEFT JOIN order_item oi ON o.order_id = oi.order_id
            WHERE o.customer_id = %s
            GROUP BY o.order_id, o.order_date, o.payment_mode, o.status
            ORDER BY o.order_id DESC;
        """
        cursor.execute(sql, (customer_id,))
        return cursor.fetchall()
