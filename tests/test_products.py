from tests.conftest import login_manager
from db import get_db_cursor

def test_product_listing(client):
    login_manager(client)
    res = client.get('/products')
    assert res.status_code == 200
    assert b"Product Catalog" in res.data

def test_product_create_and_validation(client):
    login_manager(client)

    # 1. Validation failure: Negative price
    res_bad = client.post('/products/add', data={
        'product_name': 'Test Negative Price Product',
        'price': '-15.00',
        'stock_qty': '10',
        'reorder_level': '5'
    }, follow_redirects=True)
    assert b"Price must be strictly positive" in res_bad.data

    # 2. Validation failure: Negative stock
    res_bad2 = client.post('/products/add', data={
        'product_name': 'Test Negative Stock Product',
        'price': '50.00',
        'stock_qty': '-5',
        'reorder_level': '5'
    }, follow_redirects=True)
    assert b"Stock quantity cannot be negative" in res_bad2.data

    # 3. Successful product addition
    res_ok = client.post('/products/add', data={
        'product_name': 'Automated Test Organic Honey',
        'price': '350.00',
        'category': 'Organic',
        'stock_qty': '25',
        'reorder_level': '10'
    }, follow_redirects=True)
    assert res_ok.status_code == 200
    assert b"created successfully" in res_ok.data

def test_product_soft_delete_and_restore(client):
    login_manager(client)

    # Find the created test product ID
    with get_db_cursor('manager') as (conn, cursor):
        cursor.execute("SELECT product_id FROM product WHERE product_name = 'Automated Test Organic Honey' LIMIT 1;")
        row = cursor.fetchone()
        assert row is not None, "Product should exist in database"
        pid = row['product_id']

    # Soft delete
    res_soft = client.post(f'/products/soft-delete/{pid}', follow_redirects=True)
    assert res_soft.status_code == 200
    assert b"soft-deleted" in res_soft.data.lower()

    # Verify is_active == 0 in DB
    with get_db_cursor('manager') as (conn, cursor):
        cursor.execute("SELECT is_active FROM product WHERE product_id = %s;", (pid,))
        assert cursor.fetchone()['is_active'] == 0

    # Restore
    res_restore = client.post(f'/products/restore/{pid}', follow_redirects=True)
    assert res_restore.status_code == 200
    assert b"restored" in res_restore.data.lower()

    # Verify is_active == 1 in DB
    with get_db_cursor('manager') as (conn, cursor):
        cursor.execute("SELECT is_active FROM product WHERE product_id = %s;", (pid,))
        assert cursor.fetchone()['is_active'] == 1

def test_restock_stored_procedure(client):
    login_manager(client)

    with get_db_cursor('manager') as (conn, cursor):
        cursor.execute("SELECT product_id, stock_qty FROM product WHERE product_name = 'Automated Test Organic Honey' LIMIT 1;")
        row = cursor.fetchone()
        pid = row['product_id']
        old_stock = row['stock_qty']

    # Call restock route (executes sp_restock_product)
    res = client.post('/products/restock', data={
        'product_id': str(pid),
        'quantity': '15'
    }, follow_redirects=True)
    assert res.status_code == 200
    assert b"Successfully restocked" in res.data

    # Check updated stock in DB
    with get_db_cursor('manager') as (conn, cursor):
        cursor.execute("SELECT stock_qty FROM product WHERE product_id = %s;", (pid,))
        new_stock = cursor.fetchone()['stock_qty']
        assert new_stock == old_stock + 15
