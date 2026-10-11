import mysql.connector

conn = mysql.connector.connect(
    host='localhost',
    user='shop_manager',
    password='Manager@123',
    database='grocery_shop_db'
)
cursor = conn.cursor()

cursor.execute("SHOW FULL TABLES WHERE Table_type = 'VIEW';")
views = cursor.fetchall()
print('Views:', views)

cursor.execute('SHOW TRIGGERS;')
triggers = cursor.fetchall()
print('Triggers:', [t[0] for t in triggers])

cursor.execute("SHOW PROCEDURE STATUS WHERE Db = 'grocery_shop_db';")
procs = cursor.fetchall()
print('Procedures:', [p[1] for p in procs])

conn.close()
