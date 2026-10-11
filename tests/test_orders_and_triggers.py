from tests.conftest import login_clerk, login_manager
from db import get_db_cursor

def test_valid_order_placement_and_triggers(client):
    login_clerk(client)

    # Pick an existing product and check stock
    with get_db_cursor('manager') as (conn, cursor):
        cursor.execute("SELECT product_id, stock_qty FROM product WHERE stock_qty >= 5 LIMIT 1;")
        prod = cursor.fetchone()
        pid = prod['product_id']
        initial_stock = prod['stock_qty']

    # Place order for 2 units
    res = client.post('/orders/place', data={
        'customer_option': 'existing',
        'customer_id': '1',
        'payment_mode': 'UPI',
        'product_id[]': [str(pid)],
        'quantity[]': ['2']
    }, follow_redirects=True)

    assert res.status_code == 200
    assert b"placed successfully" in res.data or b"INVOICE #" in res.data

    # Verify stock reduction via trg_reduce_stock
    with get_db_cursor('manager') as (conn, cursor):
        cursor.execute("SELECT stock_qty FROM product WHERE product_id = %s;", (pid,))
        updated_stock = cursor.fetchone()['stock_qty']
        assert updated_stock == initial_stock - 2

def test_trigger_stock_check_and_rollback(client):
    login_clerk(client)

    with get_db_cursor('manager') as (conn, cursor):
        cursor.execute("SELECT COUNT(*) AS total FROM orders;")
        initial_order_count = cursor.fetchone()['total']

    # Attempt to place order with quantity 999999
    res = client.post('/orders/place', data={
        'customer_option': 'existing',
        'customer_id': '1',
        'payment_mode': 'Cash',
        'product_id[]': ['1'],
        'quantity[]': ['999999']
    }, follow_redirects=True)

    assert res.status_code == 200
    assert b"Insufficient stock" in res.data or b"Rolled Back" in res.data

    # Verify transaction rollback: no order record was created
    with get_db_cursor('manager') as (conn, cursor):
        cursor.execute("SELECT COUNT(*) AS total FROM orders;")
        current_order_count = cursor.fetchone()['total']
        assert current_order_count == initial_order_count, "Order count should not have increased on rollback"

def test_order_cancellation_and_stock_restoration(client):
    login_manager(client)

    # Find the most recent active order
    with get_db_cursor('manager') as (conn, cursor):
        cursor.execute("""
            SELECT o.order_id, oi.product_id, oi.quantity, p.stock_qty
            FROM orders o
            JOIN order_item oi ON o.order_id = oi.order_id
            JOIN product p ON oi.product_id = p.product_id
            WHERE o.status != 'Cancelled'
            ORDER BY o.order_id DESC
            LIMIT 1;
        """)
        order_info = cursor.fetchone()

    assert order_info is not None
    order_id = order_info['order_id']
    pid = order_info['product_id']
    qty = order_info['quantity']
    stock_before_cancel = order_info['stock_qty']

    # Cancel the order
    res = client.post(f'/orders/{order_id}/cancel', follow_redirects=True)
    assert res.status_code == 200
    assert b"Cancelled" in res.data

    # Verify stock restored in product table
    with get_db_cursor('manager') as (conn, cursor):
        cursor.execute("SELECT stock_qty FROM product WHERE product_id = %s;", (pid,))
        restored_stock = cursor.fetchone()['stock_qty']
        assert restored_stock == stock_before_cancel + qty

        cursor.execute("SELECT status FROM orders WHERE order_id = %s;", (order_id,))
        assert cursor.fetchone()['status'] == 'Cancelled'

def test_order_pdf_download(client):
    login_clerk(client)

    with get_db_cursor('clerk') as (conn, cursor):
        cursor.execute("SELECT order_id FROM orders LIMIT 1;")
        order_id = cursor.fetchone()['order_id']

    res = client.get(f'/orders/{order_id}/pdf')
    assert res.status_code == 200
    assert res.content_type == 'application/pdf'
    assert res.data.startswith(b'%PDF')
