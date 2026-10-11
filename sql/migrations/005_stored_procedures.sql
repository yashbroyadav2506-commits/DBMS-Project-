-- Migration 005: Advanced Stored Procedures (Atomic Order Placement, Cancellation & Sales Reporting)
-- Database: grocery_shop_db

DROP PROCEDURE IF EXISTS sp_create_order_header;
DELIMITER $$
CREATE PROCEDURE sp_create_order_header(
    IN p_customer_id INT,
    IN p_payment_mode VARCHAR(20),
    OUT p_order_id INT
)
SQL SECURITY DEFINER
BEGIN
    INSERT INTO orders (customer_id, order_date, payment_mode, status)
    VALUES (p_customer_id, CURDATE(), p_payment_mode, 'Completed');
    SET p_order_id = LAST_INSERT_ID();
END$$
DELIMITER ;

DROP PROCEDURE IF EXISTS sp_cancel_order;
DELIMITER $$
CREATE PROCEDURE sp_cancel_order(
    IN p_order_id INT,
    IN p_cancelled_by VARCHAR(50)
)
SQL SECURITY DEFINER
BEGIN
    DECLARE v_status VARCHAR(20);
    DECLARE v_done INT DEFAULT FALSE;
    DECLARE v_pid INT;
    DECLARE v_qty INT;
    
    DECLARE cur_items CURSOR FOR 
        SELECT product_id, quantity FROM order_item WHERE order_id = p_order_id;
    DECLARE CONTINUE HANDLER FOR NOT FOUND SET v_done = TRUE;

    SELECT status INTO v_status FROM orders WHERE order_id = p_order_id;

    IF v_status IS NULL THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Order does not exist';
    ELSEIF v_status = 'Cancelled' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Order is already cancelled';
    ELSE
        -- Restore stock for each item in the order
        OPEN cur_items;
        read_loop: LOOP
            FETCH cur_items INTO v_pid, v_qty;
            IF v_done THEN
                LEAVE read_loop;
            END IF;
            UPDATE product SET stock_qty = stock_qty + v_qty WHERE product_id = v_pid;
        END LOOP;
        CLOSE cur_items;

        -- Update order status
        UPDATE orders SET status = 'Cancelled' WHERE order_id = p_order_id;

        -- Record in audit log
        INSERT INTO audit_log (table_name, action, record_id, old_values, new_values, changed_by)
        VALUES ('orders', 'CANCEL', p_order_id, 'status: Completed', 'status: Cancelled (Stock Restored)', p_cancelled_by);
    END IF;
END$$
DELIMITER ;

DROP PROCEDURE IF EXISTS sp_sales_report;
DELIMITER $$
CREATE PROCEDURE sp_sales_report(
    IN p_start_date DATE,
    IN p_end_date DATE
)
SQL SECURITY DEFINER
BEGIN
    SELECT 
        COUNT(DISTINCT o.order_id) AS total_orders,
        COUNT(DISTINCT o.customer_id) AS total_customers,
        IFNULL(SUM(oi.quantity), 0) AS total_items_sold,
        IFNULL(SUM(oi.quantity * oi.unit_price), 0) AS total_revenue,
        ROUND(IFNULL(SUM(oi.quantity * oi.unit_price) / NULLIF(COUNT(DISTINCT o.order_id), 0), 0), 2) AS avg_order_value
    FROM orders o
    LEFT JOIN order_item oi ON o.order_id = oi.order_id
    WHERE o.order_date BETWEEN p_start_date AND p_end_date
      AND o.status != 'Cancelled';
END$$
DELIMITER ;
