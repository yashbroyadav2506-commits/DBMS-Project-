import mysql.connector
import pytest
from config import Config

def test_clerk_mysql_privilege_denials():
    """
    Connects directly as shop_clerk to MySQL and verifies that unauthorized
    DDL and DML commands are strictly denied by the MySQL authorization engine.
    """
    conn = mysql.connector.connect(
        host=Config.DB_HOST,
        port=Config.DB_PORT,
        user=Config.CLERK_DB_USER,
        password=Config.CLERK_DB_PASS,
        database=Config.DB_NAME
    )
    cursor = conn.cursor()

    # 1. Clerk can SELECT from product
    cursor.execute("SELECT COUNT(*) FROM product;")
    assert cursor.fetchone()[0] > 0, "Clerk should have SELECT on product"

    # 2. Clerk CANNOT DELETE from product (Must raise MySQL Error 1142)
    with pytest.raises(mysql.connector.Error) as exc_info:
        cursor.execute("DELETE FROM product WHERE product_id = 999999;")
    assert exc_info.value.errno == 1142, f"Expected error 1142 (command denied), got {exc_info.value.errno}"

    # 3. Clerk CANNOT DROP any table
    with pytest.raises(mysql.connector.Error) as exc_info:
        cursor.execute("DROP TABLE product;")
    assert exc_info.value.errno == 1142

    # 4. Clerk CANNOT ALTER table schema
    with pytest.raises(mysql.connector.Error) as exc_info:
        cursor.execute("ALTER TABLE product ADD COLUMN test_col INT;")
    assert exc_info.value.errno == 1142

    # 5. Clerk CANNOT modify app_users
    with pytest.raises(mysql.connector.Error) as exc_info:
        cursor.execute("INSERT INTO app_users (username, password_hash, role) VALUES ('hacker', 'hash', 'manager');")
    assert exc_info.value.errno == 1142

    cursor.close()
    conn.close()

def test_manager_mysql_privilege_granted():
    """
    Verifies that shop_manager has full administrative privileges.
    """
    conn = mysql.connector.connect(
        host=Config.DB_HOST,
        port=Config.DB_PORT,
        user=Config.MANAGER_DB_USER,
        password=Config.MANAGER_DB_PASS,
        database=Config.DB_NAME
    )
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM product;")
    assert cursor.fetchone()[0] > 0
    cursor.close()
    conn.close()
