-- Migration 003: Audit Log Table and Product Audit Triggers
-- Database: grocery_shop_db

CREATE TABLE IF NOT EXISTS audit_log (
    log_id INT AUTO_INCREMENT PRIMARY KEY,
    table_name VARCHAR(50) NOT NULL,
    action VARCHAR(20) NOT NULL,
    record_id INT,
    old_values TEXT,
    new_values TEXT,
    changed_by VARCHAR(50) DEFAULT 'system',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    KEY idx_audit_table_record (table_name, record_id),
    KEY idx_audit_created_at (created_at)
);

DROP TRIGGER IF EXISTS trg_audit_product_insert;
DELIMITER $$
CREATE TRIGGER trg_audit_product_insert
AFTER INSERT ON product
FOR EACH ROW
BEGIN
    INSERT INTO audit_log (table_name, action, record_id, old_values, new_values, changed_by)
    VALUES (
        'product',
        'INSERT',
        NEW.product_id,
        NULL,
        CONCAT('name: ', NEW.product_name, ', price: ', NEW.price, ', stock: ', NEW.stock_qty, ', category: ', IFNULL(NEW.category, 'None')),
        CURRENT_USER()
    );
END$$
DELIMITER ;

DROP TRIGGER IF EXISTS trg_audit_product_update;
DELIMITER $$
CREATE TRIGGER trg_audit_product_update
AFTER UPDATE ON product
FOR EACH ROW
BEGIN
    INSERT INTO audit_log (table_name, action, record_id, old_values, new_values, changed_by)
    VALUES (
        'product',
        'UPDATE',
        NEW.product_id,
        CONCAT('name: ', OLD.product_name, ', price: ', OLD.price, ', stock: ', OLD.stock_qty, ', active: ', OLD.is_active),
        CONCAT('name: ', NEW.product_name, ', price: ', NEW.price, ', stock: ', NEW.stock_qty, ', active: ', NEW.is_active),
        CURRENT_USER()
    );
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
        CONCAT('name: ', OLD.product_name, ', price: ', OLD.price, ', stock: ', OLD.stock_qty),
        NULL,
        CURRENT_USER()
    );
END$$
DELIMITER ;
