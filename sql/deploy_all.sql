-- =====================================================================
-- COMPLETE PRODUCTION DEPLOYMENT SCRIPT FOR HOSTED MYSQL
-- Database: grocery_shop_db
-- Compatible with: Aiven, PlanetScale, TiDB Cloud, AWS RDS, Railway, Clever Cloud, etc.
-- =====================================================================

CREATE DATABASE IF NOT EXISTS grocery_shop_db
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE grocery_shop_db;

-- ---------------------------------------------------------------------
-- 1. DATABASE USERS & DUAL-LEVEL PRIVILEGES
-- Note: Granted for '%' (hosted/cloud/Vercel connections) and 'localhost'
-- ---------------------------------------------------------------------
CREATE USER IF NOT EXISTS 'shop_manager'@'%' IDENTIFIED BY 'Manager@123';
CREATE USER IF NOT EXISTS 'shop_clerk'@'%'   IDENTIFIED BY 'Clerk@123';
CREATE USER IF NOT EXISTS 'shop_manager'@'localhost' IDENTIFIED BY 'Manager@123';
CREATE USER IF NOT EXISTS 'shop_clerk'@'localhost'   IDENTIFIED BY 'Clerk@123';

-- Manager Privileges (Full DDL & DML)
GRANT ALL PRIVILEGES ON grocery_shop_db.* TO 'shop_manager'@'%';
GRANT ALL PRIVILEGES ON grocery_shop_db.* TO 'shop_manager'@'localhost';

-- Clerk Privileges (Strictly Restricted Access)
GRANT SELECT, INSERT ON grocery_shop_db.orders TO 'shop_clerk'@'%';
GRANT SELECT, INSERT ON grocery_shop_db.order_item TO 'shop_clerk'@'%';
GRANT SELECT ON grocery_shop_db.product TO 'shop_clerk'@'%';
GRANT SELECT ON grocery_shop_db.customer TO 'shop_clerk'@'%';
GRANT SELECT ON grocery_shop_db.brand TO 'shop_clerk'@'%';
GRANT SELECT ON grocery_shop_db.supplier TO 'shop_clerk'@'%';
GRANT SELECT ON grocery_shop_db.app_users TO 'shop_clerk'@'%';
GRANT UPDATE (stock_qty) ON grocery_shop_db.product TO 'shop_clerk'@'%';

GRANT SELECT, INSERT ON grocery_shop_db.orders TO 'shop_clerk'@'localhost';
GRANT SELECT, INSERT ON grocery_shop_db.order_item TO 'shop_clerk'@'localhost';
GRANT SELECT ON grocery_shop_db.product TO 'shop_clerk'@'localhost';
GRANT SELECT ON grocery_shop_db.customer TO 'shop_clerk'@'localhost';
GRANT SELECT ON grocery_shop_db.brand TO 'shop_clerk'@'localhost';
GRANT SELECT ON grocery_shop_db.supplier TO 'shop_clerk'@'localhost';
GRANT SELECT ON grocery_shop_db.app_users TO 'shop_clerk'@'localhost';
GRANT UPDATE (stock_qty) ON grocery_shop_db.product TO 'shop_clerk'@'localhost';

FLUSH PRIVILEGES;

-- ---------------------------------------------------------------------
-- 2. SCHEMA TABLES
-- ---------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS brand (
    brand_id INT PRIMARY KEY AUTO_INCREMENT,
    brand_name VARCHAR(50) NOT NULL UNIQUE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS supplier (
    supplier_id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    phone VARCHAR(15),
    email VARCHAR(100)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS product (
    product_id INT PRIMARY KEY AUTO_INCREMENT,
    product_name VARCHAR(100) NOT NULL,
    price DECIMAL(10,2) NOT NULL,
    category VARCHAR(50),
    brand_id INT,
    supplier_id INT,
    stock_qty INT DEFAULT 0,
    reorder_level INT DEFAULT 10,
    is_active TINYINT(1) NOT NULL DEFAULT 1,
    CONSTRAINT chk_product_price CHECK (price >= 0),
    CONSTRAINT chk_product_stock CHECK (stock_qty >= 0),
    FOREIGN KEY (brand_id) REFERENCES brand(brand_id) ON DELETE SET NULL,
    FOREIGN KEY (supplier_id) REFERENCES supplier(supplier_id) ON DELETE SET NULL,
    INDEX idx_product_category (category),
    INDEX idx_product_name (product_name),
    INDEX idx_product_stock_reorder (stock_qty, reorder_level)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS customer (
    customer_id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    phone VARCHAR(15),
    city VARCHAR(50),
    INDEX idx_customer_phone (phone)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS orders (
    order_id INT PRIMARY KEY AUTO_INCREMENT,
    customer_id INT NOT NULL,
    order_date DATE NOT NULL,
    payment_mode VARCHAR(20) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'Completed',
    FOREIGN KEY (customer_id) REFERENCES customer(customer_id) ON DELETE CASCADE,
    INDEX idx_orders_customer_date (customer_id, order_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS order_item (
    order_item_id INT PRIMARY KEY AUTO_INCREMENT,
    order_id INT NOT NULL,
    product_id INT NOT NULL,
    quantity INT NOT NULL,
    unit_price DECIMAL(10,2) NOT NULL,
    CONSTRAINT chk_order_item_qty CHECK (quantity > 0),
    FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES product(product_id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS app_users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NULL,
    role ENUM('manager', 'clerk') NOT NULL,
    is_active TINYINT(1) NOT NULL DEFAULT 1,
    email VARCHAR(255) UNIQUE NULL,
    google_sub VARCHAR(64) UNIQUE NULL,
    full_name VARCHAR(150) NULL,
    avatar_url VARCHAR(500) NULL,
    auth_provider ENUM('local', 'google') NOT NULL DEFAULT 'local',
    last_login DATETIME NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS access_requests (
    id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(255) NOT NULL,
    full_name VARCHAR(150) NULL,
    google_sub VARCHAR(64) NULL,
    requested_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    status ENUM('pending', 'approved', 'rejected') NOT NULL DEFAULT 'pending',
    reviewed_by VARCHAR(50) NULL,
    reviewed_at DATETIME NULL,
    INDEX idx_access_requests_email (email),
    INDEX idx_access_requests_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS audit_log (
    log_id INT AUTO_INCREMENT PRIMARY KEY,
    table_name VARCHAR(50) NOT NULL,
    action VARCHAR(20) NOT NULL,
    record_id INT NULL,
    old_values TEXT NULL,
    new_values TEXT NULL,
    changed_by VARCHAR(50) DEFAULT 'system',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_audit_table_action (table_name, action),
    INDEX idx_audit_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS price_log (
    log_id INT PRIMARY KEY AUTO_INCREMENT,
    product_id INT NOT NULL,
    old_price DECIMAL(10,2),
    new_price DECIMAL(10,2),
    changed_on DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS deleted_product_log (
    log_id INT PRIMARY KEY AUTO_INCREMENT,
    product_id INT,
    product_name VARCHAR(100),
    price DECIMAL(10,2),
    deleted_on DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS schema_migrations (
    version VARCHAR(100) PRIMARY KEY,
    applied_at DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Track all applied migration versions
INSERT IGNORE INTO schema_migrations (version) VALUES
('001_indexes_and_constraints.sql'),
('002_soft_delete_and_order_status.sql'),
('003_audit_log_and_triggers.sql'),
('004_new_views.sql'),
('005_stored_procedures.sql'),
('006_google_oauth_and_access_requests.sql');

-- ---------------------------------------------------------------------
-- 3. SEED CORE DATA (BRANDS, SUPPLIERS, PRODUCTS, USERS)
-- ---------------------------------------------------------------------

-- Demo Users (Passwords: manager123 & clerk123 hashed via scrypt/pbkdf2)
INSERT INTO app_users (id, username, password_hash, role, is_active, email, full_name, auth_provider)
VALUES 
(1, 'manager_user', 'scrypt:32768:8:1$pG7kXwZ0r6x8f1tZ$482a6f23347b7aa8d57d59b207e0c9049a4087e6fa16b04e0e5ea451877478056e4fc348ea38b68aa4cb2c3cf3d6c0df9aa2980fa86d11634812a818c3ad7bb0', 'manager', 1, 'manager@grocerydb.local', 'Store Manager', 'local'),
(2, 'clerk_user', 'scrypt:32768:8:1$n4r4Z1k7VpQz3x7Y$604da5aa9c6096570c9d9f5da00a75d5fbe5b84236aee063fc7c2b512a8d380f2d93e50ea8a24c03b1d310cae765582f059bc4ce22c713f0c13bb93b2a59a35e', 'clerk', 1, 'clerk@grocerydb.local', 'Counter Clerk', 'local')
ON DUPLICATE KEY UPDATE id=id;

-- Seed Brands
INSERT INTO brand (brand_id, brand_name) VALUES
(1, 'Amul'), (2, 'Tata'), (3, 'Fortune'), (4, 'Nestle'), (5, 'Britannia'),
(6, 'Mother Dairy'), (7, 'Nandini'), (8, 'Aashirvaad'), (9, 'India Gate'), (10, 'Tata Sampann'),
(11, 'Madhur'), (12, 'Saffola'), (13, 'Patanjali'), (14, 'Daawat'), (15, 'Rajdhani'),
(16, 'Pillsbury'), (17, 'Organic Tattva'), (18, 'PepsiCo'), (19, 'Parle'), (20, 'Haldiram''s'),
(21, 'ITC'), (22, 'Mondelez'), (23, 'Cadbury'), (24, 'Act II'), (25, 'Ferrero'),
(26, 'Brooke Bond'), (27, 'Bru'), (28, 'Coca-Cola'), (29, 'Dabur'), (30, 'Bisleri'),
(31, 'Tropicana'), (32, 'Horlicks'), (33, 'Local Farm'), (34, 'HUL'), (35, 'Reckitt'),
(36, 'P&G'), (37, 'Godrej'), (38, '3M'), (39, 'Jyothy'), (40, 'Colgate'),
(41, 'Himalaya'), (42, 'Marico'), (43, 'Gillette'), (44, 'MDH'), (45, 'Everest'),
(46, 'Catch'), (47, 'Badshah'), (48, 'Maggi'), (49, 'Knorr'), (50, 'Ching''s Secret'),
(51, 'Kissan'), (52, 'Del Monte'), (53, 'Nutella')
ON DUPLICATE KEY UPDATE brand_id=brand_id;

-- Seed Suppliers
INSERT INTO supplier (supplier_id, name, phone, email) VALUES
(1, 'Metro Cash & Carry', '9811122233', 'orders@metrocash.in'),
(2, 'Delhi Wholesale Mart', '9822233344', 'contact@delhiwholesale.com'),
(3, 'Fresh Farm Agro Traders', '9833344455', 'sales@freshfarmagro.com'),
(4, 'Godrej Consumer Supplies', '9844455566', 'care@godrejdist.com'),
(5, 'Hindustan Unilever Depot', '9855566677', 'orders@hulsupply.in'),
(6, 'ITC Logistics Hub', '9866677788', 'b2b@itcdist.com'),
(7, 'Nestle India Distribution', '9877788899', 'supply@nestledepot.in'),
(8, 'Parle Agro Wholesale', '9888899900', 'dispatch@parleagro.in')
ON DUPLICATE KEY UPDATE supplier_id=supplier_id;

-- Seed Core Sample Products
INSERT INTO product (product_id, product_name, price, category, brand_id, supplier_id, stock_qty, reorder_level, is_active) VALUES
(1, 'Amul Taaza Milk 1L', 68.00, 'Dairy', 1, 1, 50, 15, 1),
(2, 'Tata Salt 1kg', 28.00, 'Staples', 2, 2, 80, 20, 1),
(3, 'Fortune Sunlite Sunflower Oil 1L', 145.00, 'Edible Oil', 3, 1, 35, 10, 1),
(4, 'Nestle Maggi 2-Minute Noodles 70g', 14.00, 'Packaged Food', 4, 1, 120, 30, 1),
(5, 'Britannia Good Day Butter Cookies 100g', 30.00, 'Bakery & Biscuits', 5, 2, 60, 15, 1),
(6, 'Amul Salted Butter 500g', 275.00, 'Dairy', 1, 1, 25, 8, 1),
(7, 'Aashirvaad Shudh Chakki Atta 5kg', 245.00, 'Staples', 8, 3, 40, 12, 1),
(8, 'India Gate Basmati Rice Feast Rozzana 1kg', 95.00, 'Staples', 9, 2, 55, 15, 1),
(9, 'Brooke Bond Red Label Tea 500g', 260.00, 'Beverages', 26, 5, 45, 10, 1),
(10, 'Bru Instant Coffee 100g', 190.00, 'Beverages', 27, 5, 30, 8, 1),
(11, 'Coca-Cola 750ml Bottle', 40.00, 'Beverages', 28, 8, 70, 20, 1),
(12, 'Colgate Strong Teeth Toothpaste 150g', 98.00, 'Personal Care', 40, 5, 65, 15, 1),
(13, 'Surf Excel Easy Wash Detergent Powder 1kg', 140.00, 'Household', 34, 5, 50, 15, 1),
(14, 'Dettol Original Liquid Handwash 200ml', 99.00, 'Personal Care', 35, 5, 40, 10, 1),
(15, 'Haldiram''s Bhujia Sev 400g', 110.00, 'Snacks', 20, 6, 85, 20, 1)
ON DUPLICATE KEY UPDATE product_id=product_id;

-- Seed Sample Customers
INSERT INTO customer (customer_id, name, phone, city) VALUES
(1, 'Rahul Sharma', '9876543210', 'Mumbai'),
(2, 'Priya Patel', '9812345678', 'Delhi'),
(3, 'Amit Verma', '9723456789', 'Bengaluru'),
(4, 'Sneha Rao', '9634567890', 'Pune'),
(5, 'Vikram Singh', '9545678901', 'Jaipur')
ON DUPLICATE KEY UPDATE customer_id=customer_id;

-- ---------------------------------------------------------------------
-- 4. DATABASE ANALYTICAL VIEWS
-- ---------------------------------------------------------------------

CREATE OR REPLACE VIEW product_details AS
SELECT p.product_id, p.product_name, p.category, p.price, p.stock_qty, p.reorder_level, p.is_active,
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
WHERE is_active = 1
GROUP BY category;

CREATE OR REPLACE VIEW low_stock_products AS
SELECT p.product_id, p.product_name, p.stock_qty, p.reorder_level, p.price, p.category,
       s.supplier_id, s.name AS supplier_name, s.phone AS supplier_phone, s.email AS supplier_email
FROM product p
LEFT JOIN supplier s ON p.supplier_id = s.supplier_id
WHERE p.stock_qty <= p.reorder_level AND p.is_active = 1;

CREATE OR REPLACE VIEW customer_spending AS
SELECT c.customer_id, c.name AS customer,
       COUNT(DISTINCT o.order_id) AS total_orders,
       IFNULL(SUM(oi.quantity * oi.unit_price), 0) AS total_spent
FROM customer c
LEFT JOIN orders o ON c.customer_id = o.customer_id
LEFT JOIN order_item oi ON o.order_id = oi.order_id
GROUP BY c.customer_id, c.name;

CREATE OR REPLACE VIEW monthly_sales_summary AS
SELECT 
    DATE_FORMAT(o.order_date, '%Y-%m') AS sale_month,
    COUNT(DISTINCT o.order_id) AS total_orders,
    IFNULL(SUM(oi.quantity * oi.unit_price), 0) AS total_revenue,
    IFNULL(SUM(oi.quantity), 0) AS total_units_sold
FROM orders o
LEFT JOIN order_item oi ON o.order_id = oi.order_id
WHERE o.status != 'Cancelled'
GROUP BY DATE_FORMAT(o.order_date, '%Y-%m')
ORDER BY sale_month DESC;

CREATE OR REPLACE VIEW customer_order_summary AS
SELECT 
    c.customer_id,
    c.name AS customer_name,
    c.phone,
    c.city,
    COUNT(DISTINCT o.order_id) AS total_orders,
    IFNULL(SUM(CASE WHEN o.status != 'Cancelled' THEN oi.quantity * oi.unit_price ELSE 0 END), 0) AS total_spent,
    MAX(o.order_date) AS last_order_date
FROM customer c
LEFT JOIN orders o ON c.customer_id = o.customer_id
LEFT JOIN order_item oi ON o.order_id = oi.order_id
GROUP BY c.customer_id, c.name, c.phone, c.city;

-- Grant View Permissions to Clerk
GRANT SELECT ON grocery_shop_db.product_details TO 'shop_clerk'@'%';
GRANT SELECT ON grocery_shop_db.category_summary TO 'shop_clerk'@'%';
GRANT SELECT ON grocery_shop_db.low_stock_products TO 'shop_clerk'@'%';
GRANT SELECT ON grocery_shop_db.customer_spending TO 'shop_clerk'@'%';
GRANT SELECT ON grocery_shop_db.monthly_sales_summary TO 'shop_clerk'@'%';
GRANT SELECT ON grocery_shop_db.customer_order_summary TO 'shop_clerk'@'%';

GRANT SELECT ON grocery_shop_db.product_details TO 'shop_clerk'@'localhost';
GRANT SELECT ON grocery_shop_db.category_summary TO 'shop_clerk'@'localhost';
GRANT SELECT ON grocery_shop_db.low_stock_products TO 'shop_clerk'@'localhost';
GRANT SELECT ON grocery_shop_db.customer_spending TO 'shop_clerk'@'localhost';
GRANT SELECT ON grocery_shop_db.monthly_sales_summary TO 'shop_clerk'@'localhost';
GRANT SELECT ON grocery_shop_db.customer_order_summary TO 'shop_clerk'@'localhost';

FLUSH PRIVILEGES;

-- ---------------------------------------------------------------------
-- 5. STORED PROCEDURES
-- ---------------------------------------------------------------------

DROP PROCEDURE IF EXISTS sp_restock_product;
DELIMITER $$
CREATE PROCEDURE sp_restock_product(IN p_id INT, IN qty INT)
BEGIN
    UPDATE product
    SET stock_qty = stock_qty + qty
    WHERE product_id = p_id;
END$$
DELIMITER ;

DROP PROCEDURE IF EXISTS sp_cancel_order;
DELIMITER $$
CREATE PROCEDURE sp_cancel_order(IN p_order_id INT, IN p_cancelled_by VARCHAR(50))
BEGIN
    DECLARE v_current_status VARCHAR(20);
    
    SELECT status INTO v_current_status FROM orders WHERE order_id = p_order_id;
    
    IF v_current_status IS NULL THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Order not found.';
    ELSEIF v_current_status = 'Cancelled' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Order is already cancelled.';
    ELSE
        -- Restore inventory quantities
        UPDATE product p
        JOIN order_item oi ON p.product_id = oi.product_id
        SET p.stock_qty = p.stock_qty + oi.quantity
        WHERE oi.order_id = p_order_id;
        
        -- Update order status
        UPDATE orders SET status = 'Cancelled' WHERE order_id = p_order_id;
        
        -- Log cancellation audit
        INSERT INTO audit_log (table_name, action, record_id, old_values, new_values, changed_by)
        VALUES ('orders', 'CANCEL_ORDER', p_order_id, CONCAT('status: ', v_current_status), 'status: Cancelled', p_cancelled_by);
    END IF;
END$$
DELIMITER ;

DROP PROCEDURE IF EXISTS sp_sales_report;
DELIMITER $$
CREATE PROCEDURE sp_sales_report(IN p_start_date DATE, IN p_end_date DATE)
BEGIN
    SELECT 
        o.order_id,
        o.order_date,
        c.name AS customer_name,
        o.payment_mode,
        o.status,
        COUNT(oi.order_item_id) AS total_items,
        IFNULL(SUM(oi.quantity * oi.unit_price), 0) AS order_total
    FROM orders o
    JOIN customer c ON o.customer_id = c.customer_id
    LEFT JOIN order_item oi ON o.order_id = oi.order_id
    WHERE o.order_date BETWEEN p_start_date AND p_end_date
    GROUP BY o.order_id, o.order_date, c.name, o.payment_mode, o.status
    ORDER BY o.order_date DESC, o.order_id DESC;
END$$
DELIMITER ;

DROP PROCEDURE IF EXISTS sp_create_order_header;
DELIMITER $$
CREATE PROCEDURE sp_create_order_header(
    IN p_customer_id INT,
    IN p_payment_mode VARCHAR(20),
    OUT p_order_id INT
)
BEGIN
    INSERT INTO orders (customer_id, order_date, payment_mode, status)
    VALUES (p_customer_id, CURDATE(), p_payment_mode, 'Completed');
    SET p_order_id = LAST_INSERT_ID();
END$$
DELIMITER ;

-- ---------------------------------------------------------------------
-- 6. TRIGGERS
-- ---------------------------------------------------------------------

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

DROP TRIGGER IF EXISTS trg_audit_product_update;
DELIMITER $$
CREATE TRIGGER trg_audit_product_update
AFTER UPDATE ON product
FOR EACH ROW
BEGIN
    IF OLD.price <> NEW.price OR OLD.stock_qty <> NEW.stock_qty THEN
        INSERT INTO audit_log (table_name, action, record_id, old_values, new_values, changed_by)
        VALUES (
            'product', 
            'UPDATE', 
            NEW.product_id, 
            CONCAT('price: ', OLD.price, ', stock: ', OLD.stock_qty), 
            CONCAT('price: ', NEW.price, ', stock: ', NEW.stock_qty), 
            'trigger'
        );
    END IF;
END$$
DELIMITER ;

DROP TRIGGER IF EXISTS trg_audit_product_delete;
DELIMITER $$
CREATE TRIGGER trg_audit_product_delete
AFTER DELETE ON product
FOR EACH ROW
BEGIN
    INSERT INTO audit_log (table_name, action, record_id, old_values, new_values, changed_by)
    VALUES (
        'product', 
        'DELETE', 
        OLD.product_id, 
        CONCAT('name: ', OLD.product_name, ', price: ', OLD.price), 
        NULL, 
        'trigger'
    );
END$$
DELIMITER ;

DROP TRIGGER IF EXISTS trg_audit_order_insert;
DELIMITER $$
CREATE TRIGGER trg_audit_order_insert
AFTER INSERT ON orders
FOR EACH ROW
BEGIN
    INSERT INTO audit_log (table_name, action, record_id, old_values, new_values, changed_by)
    VALUES (
        'orders', 
        'INSERT', 
        NEW.order_id, 
        NULL, 
        CONCAT('customer_id: ', NEW.customer_id, ', payment: ', NEW.payment_mode, ', status: ', NEW.status), 
        'trigger'
    );
END$$
DELIMITER ;

DROP TRIGGER IF EXISTS trg_log_price_change;
DELIMITER $$
CREATE TRIGGER trg_log_price_change
AFTER UPDATE ON product
FOR EACH ROW
BEGIN
    IF OLD.price <> NEW.price THEN
        INSERT INTO price_log (product_id, old_price, new_price)
        VALUES (NEW.product_id, OLD.price, NEW.price);
    END IF;
END$$
DELIMITER ;

DROP TRIGGER IF EXISTS trg_log_deleted_product;
DELIMITER $$
CREATE TRIGGER trg_log_deleted_product
AFTER DELETE ON product
FOR EACH ROW
BEGIN
    INSERT INTO deleted_product_log (product_id, product_name, price)
    VALUES (OLD.product_id, OLD.product_name, OLD.price);
END$$
DELIMITER ;

-- ---------------------------------------------------------------------
-- 7. VERIFICATION CHECK SUMMARY
-- ---------------------------------------------------------------------
SELECT '--- DEPLOYMENT VERIFICATION SUMMARY ---' AS status;

SELECT 'TABLES' AS object_type, COUNT(*) AS count 
FROM information_schema.tables 
WHERE table_schema = DATABASE() AND table_type = 'BASE TABLE'
UNION ALL
SELECT 'VIEWS' AS object_type, COUNT(*) AS count 
FROM information_schema.views 
WHERE table_schema = DATABASE()
UNION ALL
SELECT 'STORED PROCEDURES' AS object_type, COUNT(*) AS count 
FROM information_schema.routines 
WHERE routine_schema = DATABASE() AND routine_type = 'PROCEDURE'
UNION ALL
SELECT 'TRIGGERS' AS object_type, COUNT(*) AS count 
FROM information_schema.triggers 
WHERE trigger_schema = DATABASE();

SELECT user, host FROM mysql.user WHERE user IN ('shop_manager', 'shop_clerk');
