import mysql.connector

conn = mysql.connector.connect(
    host='localhost',
    user='shop_manager',
    password='Manager@123',
    database='grocery_shop_db'
)
cursor = conn.cursor()

cursor.execute("""
CREATE OR REPLACE VIEW product_details AS
SELECT p.product_id, p.product_name, p.category, p.price, p.stock_qty, p.reorder_level,
       IFNULL(b.brand_name, 'No Brand') AS brand,
       IFNULL(s.name, 'No Supplier') AS supplier
FROM product p
LEFT JOIN brand b ON p.brand_id = b.brand_id
LEFT JOIN supplier s ON p.supplier_id = s.supplier_id;
""")
conn.commit()

print("product_details view updated successfully!")
conn.close()
