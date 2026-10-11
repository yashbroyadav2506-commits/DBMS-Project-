-- Migration 002: Soft Delete & Order Status Support
-- Database: grocery_shop_db

-- Add soft delete flag to product
ALTER TABLE product ADD COLUMN is_active TINYINT(1) NOT NULL DEFAULT 1;

-- Add order lifecycle status to orders
ALTER TABLE orders ADD COLUMN status VARCHAR(20) NOT NULL DEFAULT 'Completed';

-- Add active status flag to app_users for account deactivation
ALTER TABLE app_users ADD COLUMN is_active TINYINT(1) NOT NULL DEFAULT 1;
