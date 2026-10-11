-- Migration 001: Performance Indexes and Integrity Constraints
-- Database: grocery_shop_db

-- Add indexes on product
CREATE INDEX idx_product_category ON product(category);
CREATE INDEX idx_product_name ON product(product_name);
CREATE INDEX idx_product_stock_reorder ON product(stock_qty, reorder_level);

-- Add composite index on orders
CREATE INDEX idx_orders_customer_date ON orders(customer_id, order_date);

-- Add index on customer phone for lookups
CREATE INDEX idx_customer_phone ON customer(phone);
