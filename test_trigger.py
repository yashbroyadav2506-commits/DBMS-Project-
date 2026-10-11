import mysql.connector

conn = mysql.connector.connect(
    host='localhost',
    user='shop_manager',
    password='Manager@123',
    database='grocery_shop_db'
)
cursor = conn.cursor()

try:
    cursor.execute("INSERT INTO Orders (customer_id, order_date, payment_mode) VALUES (1, CURDATE(), 'UPI');")
    order_id = cursor.lastrowid
    cursor.execute("INSERT INTO Order_Item (order_id, product_id, quantity, unit_price) VALUES (%s, 1, 99999, 275.00);", (order_id,))
    conn.commit()
    print('Error: insert succeeded unexpectedly')
except mysql.connector.Error as err:
    conn.rollback()
    print('SUCCESS! Caught trigger error as expected:')
    print(f'ErrorCode: {err.errno}, SQLState: {err.sqlstate}, Message: {err.msg}')
finally:
    conn.close()
