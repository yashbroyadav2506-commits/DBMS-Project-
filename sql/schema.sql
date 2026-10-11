-- =====================================================================
-- GROCERY STORE DATABASE SCHEMA (Practical 5: DBMS Mini Project)
-- Database: grocery_shop_db
-- =====================================================================

CREATE DATABASE IF NOT EXISTS grocery_shop_db;
USE grocery_shop_db;

-- 1. Create MySQL Users and Grant Privileges
DROP USER IF EXISTS 'shop_manager'@'localhost';
DROP USER IF EXISTS 'shop_clerk'@'localhost';

CREATE USER 'shop_manager'@'localhost' IDENTIFIED BY 'Manager@123';
CREATE USER 'shop_clerk'@'localhost'   IDENTIFIED BY 'Clerk@123';

-- Manager full privileges
GRANT ALL PRIVILEGES ON grocery_shop_db.* TO 'shop_manager'@'localhost';

-- Clerk restricted privileges
GRANT SELECT, INSERT ON grocery_shop_db.orders TO 'shop_clerk'@'localhost';
GRANT SELECT, INSERT ON grocery_shop_db.order_item TO 'shop_clerk'@'localhost';
GRANT SELECT ON grocery_shop_db.product TO 'shop_clerk'@'localhost';
GRANT SELECT ON grocery_shop_db.customer TO 'shop_clerk'@'localhost';
GRANT SELECT ON grocery_shop_db.brand TO 'shop_clerk'@'localhost';
GRANT SELECT ON grocery_shop_db.supplier TO 'shop_clerk'@'localhost';
GRANT SELECT ON grocery_shop_db.app_users TO 'shop_clerk'@'localhost';
GRANT UPDATE (stock_qty) ON grocery_shop_db.product TO 'shop_clerk'@'localhost';

FLUSH PRIVILEGES;

-- 2. Create Core Tables
CREATE TABLE IF NOT EXISTS brand (
    brand_id INT PRIMARY KEY AUTO_INCREMENT,
    brand_name VARCHAR(50) NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS supplier (
    supplier_id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    phone VARCHAR(15),
    email VARCHAR(100)
);

CREATE TABLE IF NOT EXISTS product (
    product_id INT PRIMARY KEY AUTO_INCREMENT,
    product_name VARCHAR(100) NOT NULL,
    price DECIMAL(10,2) NOT NULL,
    category VARCHAR(50),
    brand_id INT,
    supplier_id INT,
    stock_qty INT DEFAULT 0,
    reorder_level INT DEFAULT 10,
    FOREIGN KEY (brand_id) REFERENCES brand(brand_id) ON DELETE SET NULL,
    FOREIGN KEY (supplier_id) REFERENCES supplier(supplier_id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS customer (
    customer_id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    phone VARCHAR(15),
    city VARCHAR(50)
);

CREATE TABLE IF NOT EXISTS orders (
    order_id INT PRIMARY KEY AUTO_INCREMENT,
    customer_id INT NOT NULL,
    order_date DATE NOT NULL,
    payment_mode VARCHAR(20) NOT NULL,
    FOREIGN KEY (customer_id) REFERENCES customer(customer_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS order_item (
    order_item_id INT PRIMARY KEY AUTO_INCREMENT,
    order_id INT NOT NULL,
    product_id INT NOT NULL,
    quantity INT NOT NULL,
    unit_price DECIMAL(10,2) NOT NULL,
    FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES product(product_id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS app_users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('manager', 'clerk') NOT NULL
);

CREATE TABLE IF NOT EXISTS price_log (
    log_id INT PRIMARY KEY AUTO_INCREMENT,
    product_id INT NOT NULL,
    old_price DECIMAL(10,2),
    new_price DECIMAL(10,2),
    changed_on DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS deleted_product_log (
    log_id INT PRIMARY KEY AUTO_INCREMENT,
    product_id INT,
    product_name VARCHAR(100),
    price DECIMAL(10,2),
    deleted_on DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 3. Create Views
CREATE OR REPLACE VIEW product_details AS
SELECT p.product_id, p.product_name, p.category, p.price, p.stock_qty, p.reorder_level,
       IFNULL(b.brand_name, 'No Brand') AS brand,
       IFNULL(s.name, 'No Supplier') AS supplier
FROM product p
LEFT JOIN brand b ON p.brand_id = b.brand_id
LEFT JOIN supplier s ON p.supplier_id = s.supplier_id;

CREATE OR REPLACE VIEW category_summary AS
SELECT category, COUNT(*) AS total_products,
       ROUND(AVG(price), 2) AS avg_price,
       SUM(stock_qty) AS total_stock
FROM product
GROUP BY category;

CREATE OR REPLACE VIEW low_stock_products AS
SELECT product_id, product_name, stock_qty, reorder_level, price, category
FROM product
WHERE stock_qty <= reorder_level;

CREATE OR REPLACE VIEW customer_spending AS
SELECT c.customer_id, c.name AS customer,
       COUNT(DISTINCT o.order_id) AS total_orders,
       IFNULL(SUM(oi.quantity * oi.unit_price), 0) AS total_spent
FROM customer c
LEFT JOIN orders o ON c.customer_id = o.customer_id
LEFT JOIN order_item oi ON o.order_id = oi.order_id
GROUP BY c.customer_id, c.name;

-- Grant SELECT on views to clerk
GRANT SELECT ON grocery_shop_db.product_details TO 'shop_clerk'@'localhost';
GRANT SELECT ON grocery_shop_db.category_summary TO 'shop_clerk'@'localhost';
GRANT SELECT ON grocery_shop_db.low_stock_products TO 'shop_clerk'@'localhost';
GRANT SELECT ON grocery_shop_db.customer_spending TO 'shop_clerk'@'localhost';
FLUSH PRIVILEGES;

-- 4. Create Stored Procedures
DROP PROCEDURE IF EXISTS sp_restock_product;
DELIMITER $$
CREATE PROCEDURE sp_restock_product(IN p_id INT, IN qty INT)
BEGIN
    UPDATE product
    SET stock_qty = stock_qty + qty
    WHERE product_id = p_id;
END$$
DELIMITER ;

-- 5. Create Triggers
DROP TRIGGER IF EXISTS trg_check_stock;
DELIMITER $$
CREATE TRIGGER trg_check_stock
BEFORE INSERT ON order_item
FOR EACH ROW
BEGIN
    DECLARE v_available INT;
    SELECT stock_qty INTO v_available
    FROM product
    WHERE product_id = NEW.product_id;

    IF NEW.quantity > v_available THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Insufficient stock for this product';
    END IF;
END$$
DELIMITER ;

DROP TRIGGER IF EXISTS trg_reduce_stock;
DELIMITER $$
CREATE TRIGGER trg_reduce_stock
AFTER INSERT ON order_item
FOR EACH ROW
BEGIN
    UPDATE product
    SET stock_qty = stock_qty - NEW.quantity
    WHERE product_id = NEW.product_id;
END$$
DELIMITER ;
