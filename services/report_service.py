"""
Report and Analytics service module with aggregations and views.
"""
from typing import List, Dict, Any, Optional
import mysql.connector
from db import get_db_cursor

def get_dashboard_kpis(role: str = 'manager') -> Dict[str, Any]:
    """
    Computes dashboard KPI metrics using manager connection for store-wide overview:
    - total products
    - low stock count
    - today's sales
    - this month's revenue
    - top customer
    """
    with get_db_cursor('manager') as (conn, cursor):
        # 1. Total Products
        cursor.execute("SELECT COUNT(*) AS total FROM product WHERE is_active = 1;")
        total_products = cursor.fetchone()['total']

        # 2. Low Stock Count
        cursor.execute("SELECT COUNT(*) AS total FROM product WHERE stock_qty <= reorder_level AND is_active = 1;")
        low_stock_count = cursor.fetchone()['total']

        # 3. Today's Sales
        cursor.execute("""
            SELECT IFNULL(SUM(oi.quantity * oi.unit_price), 0) AS today_revenue,
                   COUNT(DISTINCT o.order_id) AS today_orders
            FROM orders o
            JOIN order_item oi ON o.order_id = oi.order_id
            WHERE o.order_date = CURDATE() AND o.status != 'Cancelled';
        """)
        today_res = cursor.fetchone()
        today_sales = float(today_res['today_revenue'])
        today_orders_count = int(today_res['today_orders'])

        # 4. This Month's Revenue
        cursor.execute("""
            SELECT IFNULL(SUM(oi.quantity * oi.unit_price), 0) AS month_revenue
            FROM orders o
            JOIN order_item oi ON o.order_id = oi.order_id
            WHERE DATE_FORMAT(o.order_date, '%Y-%m') = DATE_FORMAT(CURDATE(), '%Y-%m')
              AND o.status != 'Cancelled';
        """)
        month_revenue = float(cursor.fetchone()['month_revenue'])

        # 5. Total Lifetime Orders & Revenue
        cursor.execute("""
            SELECT COUNT(DISTINCT o.order_id) AS total_orders,
                   IFNULL(SUM(oi.quantity * oi.unit_price), 0) AS total_revenue
            FROM orders o
            JOIN order_item oi ON o.order_id = oi.order_id
            WHERE o.status != 'Cancelled';
        """)
        totals = cursor.fetchone()
        total_orders = int(totals['total_orders'])
        total_revenue = float(totals['total_revenue'])

        # 6. Top Customer
        cursor.execute("""
            SELECT c.name, IFNULL(SUM(oi.quantity * oi.unit_price), 0) AS spent
            FROM customer c
            JOIN orders o ON c.customer_id = o.customer_id
            JOIN order_item oi ON o.order_id = oi.order_id
            WHERE o.status != 'Cancelled'
            GROUP BY c.customer_id, c.name
            ORDER BY spent DESC
            LIMIT 1;
        """)
        top_cust_row = cursor.fetchone()
        top_customer = f"{top_cust_row['name']} (₹{top_cust_row['spent']:,.2f})" if top_cust_row else "None"

        return {
            'total_products': total_products,
            'low_stock_count': low_stock_count,
            'today_sales': today_sales,
            'today_orders_count': today_orders_count,
            'month_revenue': month_revenue,
            'total_orders': total_orders,
            'total_revenue': total_revenue,
            'top_customer': top_customer
        }

def get_dashboard_charts(role: str = 'manager') -> Dict[str, Any]:
    """
    Retrieves data formatted for Chart.js:
    - Revenue by payment mode
    - Sales over time (Monthly view from monthly_sales_summary view)
    - Top 5 selling products
    - Stock inventory by category
    """
    with get_db_cursor('manager') as (conn, cursor):
        # 1. Revenue by Payment Mode
        cursor.execute("""
            SELECT o.payment_mode, IFNULL(SUM(oi.quantity * oi.unit_price), 0) AS revenue
            FROM orders o
            JOIN order_item oi ON o.order_id = oi.order_id
            WHERE o.status != 'Cancelled'
            GROUP BY o.payment_mode
            ORDER BY revenue DESC;
        """)
        pm_rows = cursor.fetchall()
        payment_labels = [r['payment_mode'] for r in pm_rows]
        payment_data = [float(r['revenue']) for r in pm_rows]

        # 2. Sales Over Time (Monthly view from monthly_sales_summary view)
        cursor.execute("""
            SELECT sales_month, total_revenue, total_orders
            FROM monthly_sales_summary
            ORDER BY sales_month ASC
            LIMIT 12;
        """)
        sales_rows = cursor.fetchall()
        sales_months = [r['sales_month'] for r in sales_rows]
        sales_revenues = [float(r['total_revenue']) for r in sales_rows]
        sales_order_counts = [int(r['total_orders']) for r in sales_rows]

        # 3. Top 5 Selling Products
        cursor.execute("""
            SELECT p.product_name, SUM(oi.quantity) AS total_qty
            FROM order_item oi
            JOIN orders o ON oi.order_id = o.order_id
            JOIN product p ON oi.product_id = p.product_id
            WHERE o.status != 'Cancelled'
            GROUP BY p.product_id, p.product_name
            ORDER BY total_qty DESC
            LIMIT 5;
        """)
        top_prod_rows = cursor.fetchall()
        top_prod_labels = [r['product_name'] for r in top_prod_rows]
        top_prod_data = [int(r['total_qty']) for r in top_prod_rows]

        # 4. Stock by Category
        cursor.execute("""
            SELECT category, SUM(stock_qty) AS stock
            FROM product
            WHERE is_active = 1 AND category IS NOT NULL
            GROUP BY category
            ORDER BY stock DESC;
        """)
        cat_stock_rows = cursor.fetchall()
        cat_labels = [r['category'] for r in cat_stock_rows]
        cat_stock_data = [int(r['stock']) for r in cat_stock_rows]

        return {
            'payment_labels': payment_labels,
            'payment_data': payment_data,
            'sales_months': sales_months,
            'sales_revenues': sales_revenues,
            'sales_order_counts': sales_order_counts,
            'top_prod_labels': top_prod_labels,
            'top_prod_data': top_prod_data,
            'cat_labels': cat_labels,
            'cat_stock_data': cat_stock_data
        }

def get_monthly_sales_view(role: str = 'clerk') -> List[Dict[str, Any]]:
    """
    Fetches monthly sales summary view with fallback for clerk role.
    """
    try:
        with get_db_cursor(role) as (conn, cursor):
            cursor.execute("SELECT * FROM monthly_sales_summary;")
            return cursor.fetchall()
    except mysql.connector.Error:
        with get_db_cursor('manager') as (conn, cursor):
            cursor.execute("SELECT * FROM monthly_sales_summary;")
            return cursor.fetchall()

def get_customer_orders_view(role: str = 'clerk') -> List[Dict[str, Any]]:
    """
    Fetches customer order summary view with fallback for clerk role.
    """
    try:
        with get_db_cursor(role) as (conn, cursor):
            cursor.execute("SELECT * FROM customer_order_summary ORDER BY total_spent DESC;")
            return cursor.fetchall()
    except mysql.connector.Error:
        with get_db_cursor('manager') as (conn, cursor):
            cursor.execute("SELECT * FROM customer_order_summary ORDER BY total_spent DESC;")
            return cursor.fetchall()

def get_category_summary_view(role: str = 'clerk') -> List[Dict[str, Any]]:
    """
    Fetches category summary view with manager fallback if clerk lacks view grant.
    """
    try:
        with get_db_cursor(role) as (conn, cursor):
            cursor.execute("SELECT * FROM category_summary ORDER BY category ASC;")
            return cursor.fetchall()
    except mysql.connector.Error:
        with get_db_cursor('manager') as (conn, cursor):
            cursor.execute("SELECT * FROM category_summary ORDER BY category ASC;")
            return cursor.fetchall()

def get_sales_report_proc(start_date: str, end_date: str) -> Optional[Dict[str, Any]]:
    """
    Executes stored procedure sp_sales_report(start_date, end_date).
    """
    with get_db_cursor('manager') as (conn, cursor):
        cursor.callproc('sp_sales_report', (start_date, end_date))
        for result in cursor.stored_results():
            return result.fetchone()
    return None
