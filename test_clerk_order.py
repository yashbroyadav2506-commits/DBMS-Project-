import mysql.connector

try:
    conn = mysql.connector.connect(
        host='localhost',
        user='shop_clerk',
        password='Clerk@123',
        database='grocery_shop_db'
    )
    cursor = conn.cursor()
    cursor.execute("INSERT INTO Orders (customer_id, order_date, payment_mode) VALUES (1, CURDATE(), 'Cash');")
    oid = cursor.lastrowid
    cursor.execute("INSERT INTO Order_Item (order_id, product_id, quantity, unit_price) VALUES (%s, 2, 1, 68.00);", (oid,))
    conn.commit()
    print("SUCCESS: shop_clerk inserted order #", oid)
    conn.close()
except mysql.connector.Error as err:
    print("Clerk order failed:", err)
