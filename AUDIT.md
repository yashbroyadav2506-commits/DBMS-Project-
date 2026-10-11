# Comprehensive Audit Report: Grocery Store DBMS Mini Project
**Date:** October 2026  
**Project:** DBMS Practical 5: Database Connectivity with Front End Tools (Flask + MySQL)  
**Database:** `grocery_shop_db` (~108+ Products)

---

## Executive Summary
An in-depth architectural and code audit of the Flask + MySQL grocery store application was conducted prior to making any modifications. While the core application features a working baseline with role separation (`shop_manager` and `shop_clerk`), MySQL views, a stock-check trigger, and a stored procedure, significant vulnerabilities, architectural bottlenecks, performance inefficiencies, and UX limitations were identified.

---

## 1. Security Gaps
| Issue ID | Severity | Description | Impact |
|:---|:---:|:---|:---|
| **SEC-01** | **Critical** | **Missing CSRF Protection:** None of the POST endpoints (`/login`, `/products/add`, `/products/edit`, `/products/delete`, `/products/restock`, `/orders/place`, `/schema-alter`) validate CSRF tokens. | Vulnerable to Cross-Site Request Forgery attacks allowing malicious third-party sites to perform unauthorized writes. |
| **SEC-02** | **High** | **Insecure Session Configuration:** Flask `SECRET_KEY` has a predictable fallback. Cookies lack `SESSION_COOKIE_HTTPONLY`, `SESSION_COOKIE_SAMESITE = 'Lax'`, and inactivity expiration (`PERMANENT_SESSION_LIFETIME`). | Session hijacking and credential interception via client scripts. |
| **SEC-03** | **High** | **No Login Rate Limiting / Lockout:** `/login` allows unlimited authentication attempts with no rate limiting (Flask-Limiter) or account lockout. | Susceptible to automated credential stuffing and brute-force password attacks. |
| **SEC-04** | **Medium** | **Bypassed DB Privilege Separation in Order Placement:** In `blueprints/orders.py`, order placement circumvents clerk MySQL permission restrictions by silently grabbing `get_db('manager')`. | Defeats MySQL-level principle of least privilege for clerk sessions. |
| **SEC-05** | **Medium** | **Lack of User & Password Management:** No self-service password update for logged-in users, no password complexity enforcement, and no manager interface for user creation, role modification, or deactivation. | Users cannot rotate credentials; administrative user management requires direct manual SQL execution. |

---

## 2. Bugs & Reliability Issues
| Issue ID | Severity | Description | Impact |
|:---|:---:|:---|:---|
| **BUG-01** | **High** | **Lack of Connection Pooling & Leaked Cursors:** `db.py` creates unpooled individual MySQL connections on request. Cursors are opened without context managers (`with conn.cursor()`), risking connection leaks under load. | Connection starvation and degraded database responsiveness as traffic scales. |
| **BUG-02** | **High** | **Fragile Multi-step Writes:** In `orders.py`, customer creation, order header insertion, and item insertions occur across loosely coupled steps. Unhandled exceptions leave half-executed states if rollback fails. | Orphaned records and transaction inconsistency. |
| **BUG-03** | **Medium** | **Hard Deletion Data Loss (FK 1451):** Deleting products relies on `DELETE FROM product`, which either crashes with FK constraint failure when referenced by order items or permanently deletes product records. | Loss of historical sales analytics and order item integrity. |
| **BUG-04** | **Medium** | **Raw SQL Error Disclosure:** Raw MySQL error messages (`err.msg`) are surfaced directly to end-users in UI flash messages. 500 internal errors are not recorded to a persistent rotating log file (`logs/app.log`). | Information disclosure of table structures and constraint names to users; lack of operational observability. |

---

## 3. Missing Validation
| Issue ID | Severity | Description | Impact |
|:---|:---:|:---|:---|
| **VAL-01** | **Medium** | **Missing Form State Retention:** When validation errors occur (e.g. invalid price or missing customer name), forms clear user inputs instead of persisting previous values. | Frustrating UX requiring users to retype all inputs. |
| **VAL-02** | **Medium** | **Incomplete Field Validations:** Phone numbers, email addresses, negative prices, and maximum character lengths lack strict regex and boundary checks on both client and server sides. | Corrupt or invalid contact and numerical data stored in the database. |

---

## 4. Query Performance & Missing Indexes (N+1 and Slow Queries)
| Issue ID | Severity | Description | Impact |
|:---|:---:|:---|:---|
| **PERF-01** | **High** | **N+1 Query in Order Placement:** When placing orders with multiple items, `blueprints/orders.py` executes an individual `SELECT price FROM product WHERE product_id = %s;` inside a Python loop for every item. | Multiple round-trips to the database during high-volume sales. |
| **PERF-02** | **High** | **Unpaginated Full-Table Scans (108+ Products):** `/products` retrieves all 108+ products without server-side `LIMIT` and `OFFSET`. `/orders` similarly queries all historical orders. | Inefficient memory consumption and slow DOM rendering as the catalog expands. |
| **PERF-03** | **Medium** | **Missing Database Indexes:** While primary keys and basic foreign keys exist, critical query paths lack indexes: `product(category)`, `product(product_name)`, `orders(customer_id, order_date)`, `order_item(order_id)`, and `order_item(product_id)`. | Full table scans on sorting, filtering, and aggregation queries. |
| **PERF-04** | **Medium** | **Uncached Dashboard Metrics:** Every visit to `/dashboard` executes 5 separate statistical queries (`COUNT(*)`, `SUM(quantity * unit_price)`, `low_stock_products` view, etc.) with zero caching. | High database CPU load on frequent dashboard refreshes. |

---

## 5. Duplicated Code & Architectural Gaps
| Issue ID | Severity | Description | Impact |
|:---|:---:|:---|:---|
| **ARCH-01** | **Medium** | **Lack of Central Repository / Service Layer:** SQL queries are embedded directly inside Flask route handler functions, mingling business logic, HTTP routing, and database access. | Difficult to unit test, duplicate SQL logic across routes, and brittle maintenance. |
| **ARCH-02** | **Low** | **No Automated Migration Mechanism:** Database changes are tracked only in a static `schema.sql` without versioned, idempotent migration scripts. | Impossible to reliably reproduce or upgrade schema on top of existing production data. |

---

## 6. UX / UI Deficiencies
| Issue ID | Severity | Description | Impact |
|:---|:---:|:---|:---|
| **UX-01** | **Medium** | **No Dark/Light Mode:** Interface is locked in standard Bootstrap light theme with no user theme preference toggle. | Modern user expectation for dark mode toggle missing. |
| **UX-02** | **Medium** | **Order Placement Friction:** Product selection uses basic unsearchable dropdowns without real-time price or subtotal calculation in JavaScript. | Slow checkout experience for clerks handling multiple items. |
| **UX-03** | **Low** | **No Printable / PDF Invoices or CSV Export:** No direct CSV export for reports, and invoice download requires manual browser printing without direct PDF generation. | Inconvenient for bookkeeping, customer receipt delivery, and inventory auditing. |
| **UX-04** | **Low** | **Browser Native `confirm()` Dialogs:** Destructive actions rely on native browser modal alerts rather than sleek Bootstrap modals and toast notifications. | Outdated and inconsistent look-and-feel. |

---

## Prioritized Implementation Plan
1. **Phase 2: Durability & Reliability:**
   - Implement `mysql.connector.pooling` connection pools for `shop_manager` and `shop_clerk`.
   - Add context managers for safe cursor/connection lifecycle.
   - Global 403, 404, 500 error handlers with rotating logging to `logs/app.log`.
   - Add `is_active` soft-delete column with manager-only restore.
   - Add `audit_log` table with triggers on product changes and restocks, plus Audit Log page.
   - Versioned idempotent migrations in `sql/migrations/`.
2. **Phase 3: Security Hardening:**
   - Flask-WTF CSRF protection on all forms.
   - Secure cookie attributes (`HttpOnly`, `SameSite=Lax`, inactivity timeout).
   - Rate limiting on `/login` via Flask-Limiter.
   - Self-service password change page and Manager user management.
   - Strict privilege testing for clerk vs manager.
3. **Phase 4: UI/UX Modernization:**
   - Bootstrap 5 responsive layout with dark/light mode toggle.
   - Server-side pagination (20 per page), live search, multi-field filters, color badges.
   - Interactive order placement with dynamic rows, live calculation, searchable picker, and customer inline quick-add.
   - Printable receipt + ReportLab PDF download + CSV exports.
   - Dashboard KPI cards + interactive Chart.js visualizations.
4. **Phase 5: Performance Optimization:**
   - Create missing indexes and run EXPLAIN before/after, documenting results in `PERFORMANCE.md`.
   - Add `Monthly_Sales_Summary` and `Customer_Order_Summary` views.
   - Add stored procedure `sp_place_order` for atomic order creation.
   - Implement 60-second caching for dashboard and reports with write-invalidation.
5. **Phase 6 & 7: New Features & Code Quality:**
   - Low-stock alert banner with 1-click supplier restock list.
   - Customer, Brand, and Supplier CRUD management.
   - Order search, status filter, and order cancellation with stock restoration.
   - Global search bar.
   - Layered architecture with repository/service classes, type hints, docstrings, and comprehensive pytest test suite.
