# CHANGELOG: Grocery Store DBMS Mini Project Upgrade
**Project:** DBMS Practical 5 - Database Connectivity with Front End Tools  
**Database:** `grocery_shop_db`  
**Version:** 2.0.0 (Production-Grade Enhanced Edition)  
**Date:** October 2026

---

## [2.2.0] - Vercel Serverless Deployment Architecture

### Added
- **Serverless & Vercel Runtime Support:**
  - Standard WSGI entrypoint exposed at root in `app.py`.
  - Added `vercel.json` with `@vercel/python` builder and edge static asset routing for `/static/(.*)` to `/public/`.
  - Added `public/` directory with `favicon.svg` and `robots.txt`.
  - Configured `ProxyFix` middleware (`x_for=1, x_proto=1, x_host=1, x_prefix=1`) ensuring accurate HTTPS scheme and host header resolution behind reverse proxies.
- **Observability & Logging Refactoring:**
  - Removed all file-based logging and directory creation (`logs/app.log`); converted logging pipeline to cloud-native `sys.stdout` stream logging.
  - Added `/health` probe route verifying active MySQL connectivity via `SELECT 1` (returns HTTP 200 when healthy, HTTP 503 when disconnected).
- **Serverless Database Resilience (`db.py`):**
  - Implemented automatic connection pre-ping (`conn.ping(reconnect=True, attempts=3, delay=1)`) to automatically re-authenticate dropped or idle sockets.
  - Small, configurable connection pooling (`DB_POOL_SIZE` defaulting to 2 on Vercel).
  - Configurable SSL parameters (`DB_SSL_CA`, `DB_SSL_MODE`, `DB_SSL_DISABLED`) for cloud providers (Aiven, PlanetScale, TiDB, AWS RDS).
  - Explicit connection and read timeouts (`DB_CONNECT_TIMEOUT`, `DB_READ_TIMEOUT`).
  - Added `DatabaseUnreachableError` and custom 503 error handler rendering friendly instructions when MySQL is inaccessible.
- **Fail-Fast Configuration & Environment Variables (`config.py`):**
  - Enforced fail-fast check throwing `RuntimeError` if `SECRET_KEY` is missing in production environments.
  - Configurable cache and rate limit storage: in-memory default with optional `REDIS_URL` support.
  - Added comprehensive `.gitignore` and updated `.env.example`.
- **Cloud Database Provisioning (`sql/deploy_all.sql`):**
  - Single standalone SQL deployment script provisioning all 12 tables, 6 analytical views, 4 stored procedures, 7 triggers, users, grants for `'%'` and `'localhost'`, seed data, and a verification summary block.

---

## [2.1.0] - Google OAuth 2.0 / OpenID Connect & Access Control

### Added
- **Google OAuth 2.0 / OpenID Connect Integration (`Authlib`):**
  - Standard OpenID Connect discovery flow against `https://accounts.google.com/.well-known/openid-configuration`.
  - State and nonce CSRF validation, OpenID claims verification (`sub`, `email`, `email_verified`, `name`, `picture`).
  - Strict separation of Identity (Google) and Authorization (`app_users` table). Roles (`manager`, `clerk`) are strictly dictated by the local database.
- **Database Migration `006_google_oauth_and_access_requests.sql`:**
  - Extended `app_users` table with `email VARCHAR(255) UNIQUE NULL`, `google_sub VARCHAR(64) UNIQUE NULL`, `full_name`, `avatar_url`, `auth_provider ENUM('local','google')`, `last_login`, and nullable `password_hash`.
  - Created `access_requests` table (`id`, `email`, `full_name`, `google_sub`, `requested_at`, `status ENUM('pending','approved','rejected')`, `reviewed_by`, `reviewed_at`) for pending user authorization.
- **Manager Access Requests Authorization (`/admin/access-requests`):**
  - Dedicated manager interface to review incoming Google SSO requests with **Approve** (assigning role: `clerk` or `manager`) and **Reject** actions.
  - Dynamic navbar badge indicating pending access request count in real time.
- **User Management Enhancements (`/admin/users`):**
  - **Google Pre-Authorization:** Allows managers to pre-authorize any Google email address with a designated role before that person ever logs in.
  - Multi-identity user listing displaying avatars/initials, full name, username, email, provider badges (Google vs. Local), role, status, and last login timestamps.
  - Safety rules preventing managers from demoting or deactivating their own session, and strictly blocking removal or demotion of the last active manager in the system.
- **Access Control & Bootstrapping:**
  - `INITIAL_MANAGER_EMAIL`: First-manager bootstrap promoting designated initial email to active manager on first Google login.
  - `ALLOWED_EMAIL_DOMAINS`: Optional domain-level filtering for corporate/institutional restrictions.
  - Friendly status pages for pending approval, unverified Google email, domain restriction, deactivated accounts, and OAuth cancellation.
- **Automated Test Suite Expansion (`tests/test_google_oauth.py`):**
  - 9 automated tests covering approved clerk Google login with route blocking, approved manager Google login with full access, unknown email pending request workflow, unverified email rejection, deactivated user rejection, domain restriction, safety rules for last manager, and existing local username/password login fallback (26 total tests passing).

---

## [2.0.0] - Upgrade Release

### Added
- **Database Migrations (`sql/migrations/`):**
  - `001_indexes_and_constraints.sql`: Added B-Tree composite and single-column indexes on `category`, `product_name`, `(stock_qty, reorder_level)`, `(customer_id, order_date)`, `(phone)`. Added CHECK constraints (`price >= 0`, `stock_qty >= 0`, `quantity > 0`).
  - `002_soft_delete_and_order_status.sql`: Added `is_active` soft-delete column to `product`, `status` column (`Completed`, `Cancelled`) to `orders`, and `is_active` to `app_users`.
  - `003_audit_log_and_triggers.sql`: Created `audit_log` table tracking actor, action, table, record ID, old values, new values, and timestamps.
  - `004_new_views.sql`: Created `monthly_sales_summary` and `customer_order_summary` analytical views. Updated `product_details` and `low_stock_products` views.
  - `005_stored_procedures.sql`: Added `sp_cancel_order` (atomic cancellation and inventory stock restoration), `sp_sales_report` (date-bounded sales reporting), and `sp_create_order_header`.
  - `migrate.py`: Idempotent automated migration runner tracking migrations in `schema_migrations`.
- **Database Connection Pooling (`db.py`):**
  - Role-specific MySQL connection pools (`pool_manager`, `pool_clerk`) with automatic session recycling and context managers (`get_db_cursor`).
  - Thread-safe transaction handling with automatic commit/rollback.
- **Security Hardening:**
  - Full CSRF protection on all POST forms via `Flask-WTF` (`CSRFProtect`).
  - Secure session cookies (`HttpOnly`, `SameSite=Lax`, 60-minute inactivity timeout).
  - Rate limiting and 60-second account lockout after 5 consecutive failed login attempts.
  - Self-service password change page for authenticated users with minimum length and strength validation.
  - Manager User Management page: user creation, role assignment, and user deactivation.
- **Reporting & Exporting:**
  - Dynamic invoice PDF generation via `ReportLab` (`/orders/<id>/pdf`).
  - CSV exports for product catalog, sales orders, monthly sales summary, and customer spending summary.
- **User Interface & Modern UX:**
  - Responsive Bootstrap 5 layout with dark/light mode toggle with theme persistence in `localStorage`.
  - Global search bar across products, customers, and orders (`/search`).
  - Interactive Order Placement page with searchable product picker, dynamic row addition/removal, live line and grand totals, stock availability warnings, and customer quick-add.
  - Printable tax invoice format with clean `@media print` styles.
  - Low-stock alert banner on dashboard with a 1-click suggested supplier restock list.
  - Customer, Supplier, and Brand management pages.
  - 4 interactive Chart.js charts on dashboard (Payment Modes, Monthly Trends, Top Selling Products, Category Distribution).
- **Automated Testing Suite (`tests/`):**
  - 17 unit and integration tests with `pytest`: authentication, role-based access control, clerk route blocking (403), clerk direct MySQL privilege denials (error 1142), product CRUD, soft delete/restore, trigger stock checking with transaction rollback, restock stored procedure, and PDF generation.
- **Operations & Durability:**
  - Backup utility `backup.py` and `backup.bat` with mysqldump and python-native SQL dump fallback.
  - Rotating file logging to `logs/app.log`.
  - Friendly error pages for 403, 404, 500 without disclosing internal database error details to users.

### Changed
- Refactored monolithic SQL queries out of route handlers into a dedicated `services/` layer (`product_service`, `order_service`, `customer_service`, `supplier_brand_service`, `report_service`, `admin_service`, `pdf_service`).
- Swapped unpaginated product catalog rendering with server-side pagination (20 items per page) to support large 108+ product datasets.
- Replaced browser `confirm()` alerts with Bootstrap confirmation modals and toasts.
- Optimized order placement to batch fetch product prices, resolving the N+1 database round-trip bottleneck.

### Fixed
- Fixed FK constraint violation (error 1451) on product deletion by introducing soft-deletion with manager-only restore.
- Fixed unhandled transaction states in multi-item order creation; trigger exceptions now roll back cleanly without leaving orphaned records.
- Fixed raw SQL error disclosures in flash messages; operational exceptions are logged to `logs/app.log` while friendly messages are displayed in the UI.
