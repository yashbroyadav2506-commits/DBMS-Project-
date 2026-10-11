import mysql.connector

# 1. Create procedure using shop_manager
conn_mgr = mysql.connector.connect(
    host='localhost',
    user='shop_manager',
    password='Manager@123',
    database='grocery_shop_db'
)
cursor_mgr = conn_mgr.cursor()
cursor_mgr.execute("DROP PROCEDURE IF EXISTS sp_create_order;")
cursor_mgr.execute("""
CREATE PROCEDURE sp_create_order(
    IN p_customer_id INT,
    IN p_payment_mode VARCHAR(20),
    OUT p_order_id INT
)
SQL SECURITY DEFINER
BEGIN
    INSERT INTO Orders (customer_id, order_date, payment_mode)
    VALUES (p_customer_id, CURDATE(), p_payment_mode);
    SET p_order_id = LAST_INSERT_ID();
END;
""")
conn_mgr.commit()
cursor_mgr.execute("GRANT EXECUTE ON PROCEDURE grocery_shop_db.sp_create_order TO 'shop_clerk'@'localhost';")
conn_mgr.commit()
conn_mgr.close()

# 2. Call procedure using shop_clerk
conn_clerk = mysql.connector.connect(
    host='localhost',
    user='shop_clerk',
    password='Clerk@123',
    database='grocery_shop_db'
)
cursor_clerk = conn_clerk.cursor()
cursor_clerk.callproc('sp_create_order', (1, 'Cash', 0))
# Fetch out variable
cursor_clerk.execute("SELECT @_sp_create_order_2;")
new_id = cursor_clerk.fetchone()[0]
print("Procedure executed by shop_clerk! New Order ID:", new_id)
conn_clerk.close()
