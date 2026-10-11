# Grocery Store DBMS Mini Project (Practical 5 - Enhanced Edition)
> **Database Connectivity with Front End Tools** — Flask 3.1, MySQL 8.0, Jinja2, Bootstrap 5, Chart.js, ReportLab

This production-grade web application connects a Python/Flask front-end to an existing MySQL database (`grocery_shop_db` with 108+ products). It strictly satisfies and expands upon all requirements of **DBMS Practical 5**: Database Creation, Modification (ALTER), Data Manipulation (INSERT/UPDATE/DELETE), Dual-Level Authorization (Roles in Flask & MySQL), Views, Stored Procedures, and Triggers with ACID Transaction protection.

---

## 🛠 Tech Stack & Architecture

- **Backend:** Python 3.14 + Flask 3.1 (Blueprints Architecture)
- **Database:** MySQL 8.0 (`mysql-connector-python` with connection pooling)
- **Security:** `Flask-WTF` (CSRF Protection), `Flask-Limiter` (Lockout after 5 failed attempts), HttpOnly/SameSite session cookies, inactivity expiration
- **Front-end:** Jinja2 templates + Bootstrap 5 + Bootstrap Icons + Chart.js + Dark/Light mode toggle (`localStorage`)
- **Reporting & Exports:** `ReportLab` (PDF Invoices), Python `csv` (Catalog and Financial CSV exports)
- **Testing:** `pytest` (17 automated unit and integration tests)
- **Migrations:** Versioned, idempotent migrations in `sql/migrations/` via `migrate.py`
- **Logging & Observability:** Serverless-friendly `stdout` logging (cloud & container native) with rotating file backup utility (`backup.py`, `backup.bat`)
- **Deployment:** Vercel serverless-ready with `vercel.json`, Werkzeug `ProxyFix`, edge static routing (`public/`), and `/health` probe

---

## 🔑 Demo Credentials & Dual-Level Role Enforcement

| Role | App Username | App Password | MySQL DB User | MySQL Privileges | Application Privileges |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Manager** | `manager_user` | `manager123` | `shop_manager` | Full Access (`ALL PRIVILEGES`) | Full access: Catalog CRUD, Soft Delete/Restore, Restock, Users, Audit Log, Suppliers, Brands, Alter Schema, Order Cancellation |
| **Clerk** | `clerk_user` | `clerk123` | `shop_clerk` | Restricted (`SELECT`, `INSERT` on Orders/Order_Item, `UPDATE stock_qty` on Product) | Read catalog, place sales orders, view invoices, view reports. Strictly blocked from Manager routes (HTTP 403) and blocked at MySQL engine level |

---

## 🚀 Setup & Execution Guide

### 1. Environment Setup
Activate your Python virtual environment and install dependencies:
```bash
.venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment Variables (`.env`)
Ensure `.env` exists in the project root:
```ini
SECRET_KEY=super-secret-grocery-db-key-2026
DB_HOST=localhost
DB_PORT=3306
DB_NAME=grocery_shop_db
MANAGER_DB_USER=shop_manager
MANAGER_DB_PASS=Manager@123
CLERK_DB_USER=shop_clerk
CLERK_DB_PASS=Clerk@123
DB_POOL_SIZE=5
```

### 3. Run Database Migrations
Apply all numbered, idempotent schema migrations (indexes, soft-delete, audit log, analytical views, stored procedures):
```bash
python migrate.py
# or using virtual environment:
.venv\Scripts\python.exe migrate.py
```

### 4. Start the Web Application
```bash
python app.py
# or using virtual environment:
.venv\Scripts\python.exe app.py
```
Open your browser and navigate to: **`http://127.0.0.1:5000`**

---

## 🧪 Automated Testing Suite (`pytest`)

Run the complete automated test suite (17 comprehensive tests):
```bash
.venv\Scripts\python.exe -m pytest tests/ -v
```

### What the test suite covers:
1. **Authentication & Roles (`tests/test_auth_and_roles.py`):**
   - Manager and Clerk login flows
   - Invalid credentials rejection
   - Clerk access allowed to standard store routes
   - Clerk blocked from all administrative and manager routes with **HTTP 403 Forbidden**
   - User logout and session clearing
2. **Database Engine Authorization (`tests/test_database_privileges.py`):**
   - Direct connection test as `shop_clerk` proving MySQL denies `DELETE`, `DROP`, `ALTER`, and unauthorized writes with **MySQL Error 1142**
   - Direct connection test verifying `shop_manager` administrative privileges
3. **Product Catalog & Inventory (`tests/test_products.py`):**
   - Product listing, searching, and server-side pagination
   - Product creation and server-side validation (positive price, non-negative stock)
   - Product soft-deletion (`is_active = 0`) and restoration (`is_active = 1`)
   - Stored procedure execution: `sp_restock_product` stock increment
4. **Order Placement, Triggers & Transactions (`tests/test_orders_and_triggers.py`):**
   - Valid order placement: atomic transaction with stock deduction via trigger `trg_reduce_stock`
   - Trigger stock check exception: excess quantity fires trigger `trg_check_stock`, raises error 45000, rolls back entire transaction
   - Order cancellation: stored procedure `sp_cancel_order` restores inventory stock and updates status
   - Dynamic binary PDF invoice generation with ReportLab

---

## ☁️ Deploy to Vercel (Serverless Deployment Guide)

The application is fully architected for serverless deployments on **Vercel** with zero file-system dependencies, stdout logging, lean database connection pooling with pre-ping reconnects, and `ProxyFix` middleware.

### 1. Hosted MySQL Database Options
Because Vercel functions are stateless and ephemeral, your MySQL database must be hosted on an internet-accessible cloud provider. Recommended options with free/developer tiers:
- **[Aiven for MySQL](https://aiven.io/mysql)**: Fully managed MySQL 8.0 with SSL CA bundle.
- **[TiDB Cloud (Serverless)](https://tidbcloud.com/)**: Highly available MySQL-compatible database with free tier.
- **[Railway](https://railway.app/)** / **[Clever Cloud](https://www.clever-cloud.com/)**: Instant 1-click managed MySQL.
- **[AWS RDS / Aurora](https://aws.amazon.com/rds/)**: Production enterprise MySQL.

> [!IMPORTANT]
> **Firewall / Network Rule:** In your cloud database dashboard, ensure that incoming connections from all IPs (`0.0.0.0/0`) are permitted, as Vercel routes serverless function invocations through dynamic IP pools.

---

### 2. Run the Single Deployment SQL Script
Before deploying the code, initialize all tables, analytical views, stored procedures, triggers, users, grants, and seed data in your hosted MySQL database by running:

```bash
# Using MySQL CLI:
mysql -h <CLOUD_DB_HOST> -P <PORT> -u <ADMIN_USER> -p <CLOUD_DB_NAME> < sql/deploy_all.sql
```
*(Or open [`sql/deploy_all.sql`](file:///c:/Users/Yash%20Yadav/OneDrive/Desktop/New%20folder%20(2)/DBMS%20FINAL/sql/deploy_all.sql) in MySQL Workbench, DBeaver, or TablePlus, and execute the entire script).*

The script runs a verification check at the bottom displaying your exact counts of tables (12), views (6), stored procedures (4), and triggers (7).

---

### 3. Deploy to Vercel

1. Push your repository to GitHub, GitLab, or Bitbucket.
2. Log in to [Vercel](https://vercel.com/) and click **Add New... > Project**.
3. Import your repository. Vercel automatically detects [`vercel.json`](file:///c:/Users/Yash%20Yadav/OneDrive/Desktop/New%20folder%20(2)/DBMS%20FINAL/vercel.json) and uses the `@vercel/python` runtime.
4. Under **Environment Variables**, configure the following variables:

| Environment Variable | Description | Example / Recommended Value |
| :--- | :--- | :--- |
| `SECRET_KEY` | **Required.** Cryptographic session secret key | Generate via `python -c "import secrets; print(secrets.token_hex(32))"` |
| `DB_HOST` | Hostname of your cloud MySQL database | `mysql-xxxx.aivencloud.com` or `gateway01.us-east-1.prod.aws.tidbcloud.com` |
| `DB_PORT` | Port number of your cloud MySQL database | `3306` (or provider port, e.g. `11342`) |
| `DB_NAME` | Database schema name | `grocery_shop_db` |
| `MANAGER_DB_USER` | Manager MySQL username | `shop_manager` (or cloud admin user) |
| `MANAGER_DB_PASS` | Manager MySQL password | Cloud database password |
| `CLERK_DB_USER` | Clerk MySQL username | `shop_clerk` (or cloud clerk user) |
| `CLERK_DB_PASS` | Clerk MySQL password | Cloud clerk password |
| `DB_POOL_SIZE` | Lean pool size for serverless functions | `2` *(Default on Vercel)* |
| `DB_CONNECT_TIMEOUT` | Connection timeout in seconds | `10` |
| `DB_SSL_MODE` | SSL Mode for cloud databases | `REQUIRED` (or leave blank if default) |
| `DB_SSL_CA` | Path or CA cert if required by provider | Optional |
| `GOOGLE_CLIENT_ID` | Google OAuth Client ID | `your-id.apps.googleusercontent.com` |
| `GOOGLE_CLIENT_SECRET` | Google OAuth Client Secret | `your-secret` |
| `GOOGLE_REDIRECT_URI` | Production OAuth callback URI | `https://your-project.vercel.app/auth/google/callback` |
| `INITIAL_MANAGER_EMAIL`| Auto-promoted initial manager email | `your-admin-email@gmail.com` |
| `REDIS_URL` | Optional Redis URL for distributed rate limits | e.g. `rediss://default:pwd@your-upstash.com:6379` *(Optional)* |

5. Click **Deploy**. Vercel will install dependencies from `requirements.txt` and launch your serverless app.

---

### 4. Update Google Cloud Console Redirect URI
After deployment, copy your live Vercel domain (e.g., `https://grocery-db-store.vercel.app`) and update your Google Cloud Console:
1. Go to **APIs & Services > Credentials** in [Google Cloud Console](https://console.cloud.google.com/).
2. Click your OAuth 2.0 Web Client.
3. Under **Authorized redirect URIs**, add:
   ```text
   https://your-project.vercel.app/auth/google/callback
   ```
4. Save changes.

---

### 5. Health Check & Monitoring Probe
You can verify that your Vercel deployment is active and connected to your cloud MySQL database at any time by visiting:
```text
https://your-project.vercel.app/health
```
**Healthy Response (HTTP 200):**
```json
{
  "database": "connected",
  "database_host": "mysql-xxxx.aivencloud.com",
  "database_name": "grocery_shop_db",
  "status": "healthy",
  "timestamp": 1791745424
}
```

---

### 6. Vercel Troubleshooting & Solutions

- **503 Service Unavailable / Database Unreachable Error:**
  - *Cause:* MySQL database host is blocking connections or port is incorrect.
  - *Fix:* Ensure your hosted database security group allowlist has `0.0.0.0/0` enabled, and verify `DB_HOST` and `DB_PORT`.
- **`redirect_uri_mismatch` during Google Sign-In:**
  - *Cause:* The URI registered in Google Cloud Console doesn't exactly match the Vercel HTTPS domain.
  - *Fix:* Make sure `https://<your-project>.vercel.app/auth/google/callback` is added under Authorized redirect URIs in Google Cloud Console, and `GOOGLE_REDIRECT_URI` matches it in Vercel environment variables.
- **Function Timeout (>10 seconds):**
  - *Cause:* Latency between Vercel region and MySQL database region.
  - *Fix:* In your `vercel.json` or project settings, select the Vercel function region closest to your cloud database provider (e.g. `iad1` for US-East or `bom1` for Mumbai).
- **Session or CSRF Issues Behind Vercel:**
  - *Fix:* Werkzeug's `ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)` is automatically active, ensuring correct HTTPS scheme and cookie SameSite=Lax behavior.

---

## 🔑 Google Login Setup (OAuth 2.0 / OpenID Connect)

The application supports **Sign in with Google** using OpenID Connect (via `Authlib`), maintaining strict separation between **Identity Verification** and **Role Authorization**. Google proves who the user is, but only your MySQL `app_users` database determines what they can do (`manager` vs. `clerk`).

### 1. Google Cloud Console Setup Steps

To enable Google sign-in for your local and production environments:

1. **Create a Google Cloud Project:**
   - Navigate to the [Google Cloud Console](https://console.cloud.google.com/).
   - Click the project dropdown at the top and select **New Project** (e.g., `Grocery-Store-DBMS`).

2. **Configure the OAuth Consent Screen:**
   - In the left sidebar, go to **APIs & Services > OAuth consent screen**.
   - Choose User Type: **External** (or Internal if using Google Workspace) and click **Create**.
   - Fill in App Information:
     - **App name:** `Grocery Store DBMS`
     - **User support email:** Select your email.
     - **Developer contact email:** Enter your email.
   - Click **Save and Continue**.
   - **Scopes:** Click **Add or Remove Scopes**, select `openid`, `.../auth/userinfo.email`, and `.../auth/userinfo.profile`, then click **Save and Continue**.
   - **Test Users:** While in Testing mode, click **+ Add Users** and add any Google accounts you want to test with (e.g. your personal Gmail). Click **Save and Continue**.

3. **Create OAuth 2.0 Client ID Credentials:**
   - In the left sidebar, go to **APIs & Services > Credentials**.
   - Click **+ CREATE CREDENTIALS** at the top and select **OAuth client ID**.
   - Set Application Type to **Web application**.
   - **Name:** `Grocery DBMS Web Client`.
   - Under **Authorized redirect URIs**, click **+ ADD URI** and enter:
     ```text
     http://localhost:5000/auth/google/callback
     ```
     *(Add your production URL here when deploying live).*
   - Click **Create**. A modal will display your **Client ID** and **Client Secret**.

4. **Add Credentials to `.env`:**
   Open `.env` in the project root and populate the keys:
   ```env
   GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
   GOOGLE_CLIENT_SECRET=your-client-secret
   GOOGLE_REDIRECT_URI=http://localhost:5000/auth/google/callback

   # Optional: Restrict logins to company domain (comma-separated, empty = any domain)
   ALLOWED_EMAIL_DOMAINS=

   # First-Manager Bootstrap: Automatically promotes this email to manager on initial login
   INITIAL_MANAGER_EMAIL=admin@example.com
   ```

5. **Run the Database Migration:**
   ```bash
   .venv\Scripts\python.exe migrate.py
   ```
   *(Migration `006_google_oauth_and_access_requests.sql` extends `app_users` and creates `access_requests`).*

---

### 🛡️ User Access & Authorization Lifecycle

```
[User clicks "Continue with Google"]
               │
               ▼
   [Google OpenID Verification] ──(email_verified = False)──► ❌ Rejected: Unverified Email
               │
   (Domain check: ALLOWED_EMAIL_DOMAINS) ──(Disallowed)─────► ❌ Rejected: Domain Not Allowed
               │
               ▼
[Lookup app_users by google_sub / email]
        │                           │
  (User exists)               (User not found)
        │                           │
        ▼                           ▼
(Active check: is_active=1)   [Create row in access_requests]
 ├── Yes: Log in as stored   [Display friendly Pending Approval page]
 │        role (Manager/Clerk)      │
 └── No:  ❌ Deactivated            ▼
                             [Manager reviews in "Access Requests"]
                             [Selects Role: Clerk or Manager -> Approve]
                                    │
                                    ▼
                             [app_users row created/activated]
                             [User logs in immediately on next attempt]
```

- **Pre-Authorization:** A store manager can navigate to **Management > User Accounts > Pre-Authorize Google User** and enter any Google email with an assigned role before that person ever logs in.
- **Safety Guarantee:** A manager cannot demote or deactivate their own session, and the system strictly prevents removing or demoting the last remaining active manager in the store.
- **Local Fallback:** Existing username/password login (`manager_user` / `clerk_user`) remains fully functional at all times.

---

## 💾 Backup and Restore Guide

### Automated Backup
Run the backup script to generate a timestamped SQL dump in `sql/backups/`:
```bash
# Via Python
python backup.py
# or Double-click:
backup.bat
```
The backup script automatically uses `mysqldump` if available, and falls back to a python-native table exporter that dumps all table schemas and records into a clean `.sql` file.

### Restore Guide
To restore the database from a backup file:
```bash
# Using MySQL Command Line:
mysql -u shop_manager -pManager@123 grocery_shop_db < sql/backups/backup_grocery_shop_db_YYYYMMDD_HHMMSS.sql

# Or using MySQL Root:
mysql -u root -p grocery_shop_db < sql/backups/backup_grocery_shop_db_YYYYMMDD_HHMMSS.sql
```

---

## 📑 Practical 5 Requirement Mapping Table

| Practical 5 Requirement | Implementation in Application | Location in Codebase |
| :--- | :--- | :--- |
| **1. Database Creation (DDL)** | Full schema initialization of tables (`brand`, `supplier`, `product`, `customer`, `orders`, `order_item`, `app_users`, `audit_log`), initial seed data, MySQL users (`shop_manager`, `shop_clerk`), and `GRANT` permissions. | [`sql/schema.sql`](file:///c:/Users/Yash%20Yadav/OneDrive/Desktop/New%20folder%20(2)/DBMS%20FINAL/sql/schema.sql)<br>[`sql/migrations/`](file:///c:/Users/Yash%20Yadav/OneDrive/Desktop/New%20folder%20(2)/DBMS%20FINAL/sql/migrations) |
| **2. Schema Modification (ALTER DDL)** | Pre-approved schema alterations (Add `discount_pct`, modify `reorder_level`, drop `discount_pct`) with strict identifier whitelisting to prevent SQL Injection, live `DESCRIBE product` inspection, and audit logging. | [`blueprints/schema_alter.py`](file:///c:/Users/Yash%20Yadav/OneDrive/Desktop/New%20folder%20(2)/DBMS%20FINAL/blueprints/schema_alter.py)<br>[`templates/schema_alter/index.html`](file:///c:/Users/Yash%20Yadav/OneDrive/Desktop/New%20folder%20(2)/DBMS%20FINAL/templates/schema_alter/index.html) |
| **3. Data Manipulation (DML)** | Form-based `INSERT`, `UPDATE`, `DELETE` across Products, Customers, Suppliers, Brands, and Orders. Server-side validations, foreign-key constraint protection (1451), and soft-delete option. | [`services/product_service.py`](file:///c:/Users/Yash%20Yadav/OneDrive/Desktop/New%20folder%20(2)/DBMS%20FINAL/services/product_service.py)<br>[`services/order_service.py`](file:///c:/Users/Yash%20Yadav/OneDrive/Desktop/New%20folder%20(2)/DBMS%20FINAL/services/order_service.py) |
| **4. Dual-Level Authorization** | - **Flask Level:** `@login_required` and `@role_required('manager')` decorators blocking clerks with HTTP 403.<br>- **MySQL Level:** Separate connection pools for `shop_manager` and `shop_clerk`. Direct MySQL queries by clerk fail with Error 1142 on unauthorized tables. | [`auth.py`](file:///c:/Users/Yash%20Yadav/OneDrive/Desktop/New%20folder%20(2)/DBMS%20FINAL/auth.py)<br>[`db.py`](file:///c:/Users/Yash%20Yadav/OneDrive/Desktop/New%20folder%20(2)/DBMS%20FINAL/db.py)<br>[`tests/test_database_privileges.py`](file:///c:/Users/Yash%20Yadav/OneDrive/Desktop/New%20folder%20(2)/DBMS%20FINAL/tests/test_database_privileges.py) |
| **5. Database Views** | - `product_details`: Joins product with brand and supplier.<br>- `category_summary`: Category product counts and average prices.<br>- `low_stock_products`: Filters inventory where `stock_qty <= reorder_level`.<br>- `monthly_sales_summary`: Monthly order aggregates and revenue.<br>- `customer_order_summary`: Customer lifetime order counts and totals. | [`sql/migrations/004_new_views.sql`](file:///c:/Users/Yash%20Yadav/OneDrive/Desktop/New%20folder%20(2)/DBMS%20FINAL/sql/migrations/004_new_views.sql)<br>[`blueprints/reports.py`](file:///c:/Users/Yash%20Yadav/OneDrive/Desktop/New%20folder%20(2)/DBMS%20FINAL/blueprints/reports.py) |
| **6. Database Triggers** | - `trg_check_stock`: BEFORE INSERT trigger on `order_item` that signals SQLSTATE 45000 if quantity exceeds stock, triggering automatic transaction rollback.<br>- `trg_reduce_stock`: AFTER INSERT trigger deducting ordered quantities from inventory.<br>- `trg_log_price_change` & `trg_log_deleted_product`: Audit tracking. | [`sql/schema.sql`](file:///c:/Users/Yash%20Yadav/OneDrive/Desktop/New%20folder%20(2)/DBMS%20FINAL/sql/schema.sql)<br>[`tests/test_orders_and_triggers.py`](file:///c:/Users/Yash%20Yadav/OneDrive/Desktop/New%20folder%20(2)/DBMS%20FINAL/tests/test_orders_and_triggers.py) |
| **7. Stored Procedures** | - `sp_restock_product(p_id, qty)`: Updates inventory stock.<br>- `sp_cancel_order(order_id, user)`: Restores stock and cancels order.<br>- `sp_sales_report(start_date, end_date)`: Computes periodic sales metrics. | [`sql/migrations/005_stored_procedures.sql`](file:///c:/Users/Yash%20Yadav/OneDrive/Desktop/New%20folder%20(2)/DBMS%20FINAL/sql/migrations/005_stored_procedures.sql)<br>[`blueprints/products.py`](file:///c:/Users/Yash%20Yadav/OneDrive/Desktop/New%20folder%20(2)/DBMS%20FINAL/blueprints/products.py) |

---

## ⚡ Performance & Index Optimization
Full query optimization details with comparative before-and-after `EXPLAIN` query execution plans are documented in [`PERFORMANCE.md`](file:///c:/Users/Yash%20Yadav/OneDrive/Desktop/New%20folder%20(2)/DBMS%20FINAL/PERFORMANCE.md).
- **86.2% query scan reduction** on product filtering by indexing `category` and `product_name`.
- Eliminated disk temporary tables on grouping queries.
- Server-side pagination (20 per page) prevents full-table DOM bloat on the 108+ product catalog.
