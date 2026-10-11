-- Migration 006: Google OAuth 2.0 and Access Requests Support
-- Database: grocery_shop_db

-- 1. Modify password_hash to allow NULL for Google SSO users
ALTER TABLE app_users MODIFY COLUMN password_hash VARCHAR(255) NULL;

-- 2. Add OAuth profile and identity columns to app_users
ALTER TABLE app_users ADD COLUMN email VARCHAR(255) NULL UNIQUE;
ALTER TABLE app_users ADD COLUMN google_sub VARCHAR(64) NULL UNIQUE;
ALTER TABLE app_users ADD COLUMN full_name VARCHAR(150) NULL;
ALTER TABLE app_users ADD COLUMN avatar_url VARCHAR(500) NULL;
ALTER TABLE app_users ADD COLUMN auth_provider ENUM('local', 'google') NOT NULL DEFAULT 'local';
ALTER TABLE app_users ADD COLUMN last_login DATETIME NULL;
ALTER TABLE app_users ADD COLUMN created_at DATETIME DEFAULT CURRENT_TIMESTAMP;

-- 3. Create access_requests table for pending user approvals
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

-- 4. Seed email and profile for existing default accounts if not set
UPDATE app_users 
SET email = 'manager@grocerydb.local', 
    full_name = 'Store Manager', 
    auth_provider = 'local' 
WHERE username = 'manager_user' AND (email IS NULL OR email = '');

UPDATE app_users 
SET email = 'clerk@grocerydb.local', 
    full_name = 'Counter Clerk', 
    auth_provider = 'local' 
WHERE username = 'clerk_user' AND (email IS NULL OR email = '');
