import mysql.connector

conn = mysql.connector.connect(
    host='localhost',
    user='shop_manager',
    password='Manager@123',
    database='grocery_shop_db'
)
cursor = conn.cursor()

cursor.execute("""
CREATE OR REPLACE VIEW low_stock_products AS
SELECT product_id, product_name, stock_qty, reorder_level, price, category
FROM product
WHERE stock_qty <= reorder_level;
""")
conn.commit()

print("low_stock_products view updated successfully!")
conn.close()
