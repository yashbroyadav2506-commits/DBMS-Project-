-- Migration 004: New Analytical Views (Monthly_Sales_Summary & Customer_Order_Summary)
-- Database: grocery_shop_db

-- 1. Monthly Sales Summary View
CREATE OR REPLACE VIEW monthly_sales_summary AS
SELECT 
    DATE_FORMAT(o.order_date, '%Y-%m') AS sales_month,
    COUNT(DISTINCT o.order_id) AS total_orders,
    IFNULL(SUM(oi.quantity), 0) AS total_items_sold,
    IFNULL(SUM(oi.quantity * oi.unit_price), 0) AS total_revenue,
    ROUND(IFNULL(SUM(oi.quantity * oi.unit_price) / NULLIF(COUNT(DISTINCT o.order_id), 0), 0), 2) AS avg_order_value
FROM orders o
LEFT JOIN order_item oi ON o.order_id = oi.order_id
WHERE o.status != 'Cancelled'
GROUP BY DATE_FORMAT(o.order_date, '%Y-%m')
ORDER BY sales_month DESC;

-- 2. Customer Order Summary View
CREATE OR REPLACE VIEW customer_order_summary AS
SELECT 
    c.customer_id,
    c.name AS customer_name,
    c.phone,
    c.city,
    COUNT(DISTINCT CASE WHEN o.status != 'Cancelled' THEN o.order_id END) AS completed_orders,
    IFNULL(SUM(CASE WHEN o.status != 'Cancelled' THEN oi.quantity * oi.unit_price ELSE 0 END), 0) AS total_spent,
    MAX(o.order_date) AS last_order_date
FROM customer c
LEFT JOIN orders o ON c.customer_id = o.customer_id
LEFT JOIN order_item oi ON o.order_id = oi.order_id
GROUP BY c.customer_id, c.name, c.phone, c.city;

-- 3. Update product_details view to include is_active
CREATE OR REPLACE VIEW product_details AS
SELECT 
    p.product_id, 
    p.product_name, 
    p.category, 
    p.price, 
    p.stock_qty, 
    p.reorder_level,
    p.is_active,
    IFNULL(b.brand_name, 'No Brand') AS brand,
    IFNULL(s.name, 'No Supplier') AS supplier
FROM product p
LEFT JOIN brand b ON p.brand_id = b.brand_id
LEFT JOIN supplier s ON p.supplier_id = s.supplier_id;

-- 4. Update low_stock_products view
CREATE OR REPLACE VIEW low_stock_products AS
SELECT 
    p.product_id, 
    p.product_name, 
    p.stock_qty, 
    p.reorder_level, 
    p.price, 
    p.category,
    p.is_active,
    IFNULL(s.name, 'No Supplier') AS supplier_name,
    IFNULL(s.phone, 'N/A') AS supplier_phone,
    IFNULL(b.brand_name, 'No Brand') AS brand_name
FROM product p
LEFT JOIN supplier s ON p.supplier_id = s.supplier_id
LEFT JOIN brand b ON p.brand_id = b.brand_id
WHERE p.stock_qty <= p.reorder_level AND p.is_active = 1;
