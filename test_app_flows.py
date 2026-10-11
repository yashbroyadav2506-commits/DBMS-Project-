import re
import urllib.request
import urllib.parse
import http.cookiejar

BASE_URL = 'http://127.0.0.1:5000'

def extract_csrf_token(html: str) -> str:
    match = re.search(r'name="csrf_token"\s+value="([^"]+)"', html)
    if match:
        return match.group(1)
    match_meta = re.search(r'content="([^"]+)"\s+name="csrf-token"', html)
    if match_meta:
        return match_meta.group(1)
    return ""

def run_tests():
    print("--- Starting End-to-End Application Flow Tests ---")
    
    # Cookie jar to persist session cookies across requests
    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

    # 1. GET Login Page
    res = opener.open(f"{BASE_URL}/login")
    assert res.status == 200, "Login page GET failed"
    html_login = res.read().decode('utf-8')
    csrf_token = extract_csrf_token(html_login)
    print("[OK] GET /login - 200 OK (CSRF extracted)")

    # 2. POST Login as Manager
    login_data = urllib.parse.urlencode({
        'csrf_token': csrf_token,
        'username': 'manager_user',
        'password': 'manager123'
    }).encode('utf-8')
    res_mgr = opener.open(f"{BASE_URL}/login", data=login_data)
    assert res_mgr.status == 200, "Manager login failed"
    body = res_mgr.read().decode('utf-8')
    assert "MANAGER" in body or "Welcome back" in body, "Manager welcome message missing"
    print("[OK] POST /login (manager_user) - Success")

    # 3. Manager Access Restricted Pages
    for path in ['/dashboard', '/products', '/products/add', '/products/restock', '/orders', '/orders/place', '/reports', '/schema-alter', '/admin/users', '/admin/audit-log', '/suppliers', '/brands']:
        r = opener.open(f"{BASE_URL}{path}")
        assert r.status == 200, f"Manager failed to access {path}"
        print(f"[OK] Manager GET {path} - 200 OK")

    # 4. Manager Execute Restock Procedure
    r_restock_get = opener.open(f"{BASE_URL}/products/restock")
    csrf_restock = extract_csrf_token(r_restock_get.read().decode('utf-8'))
    restock_data = urllib.parse.urlencode({
        'csrf_token': csrf_restock,
        'product_id': '1',
        'quantity': '5'
    }).encode('utf-8')
    r_restock = opener.open(f"{BASE_URL}/products/restock", data=restock_data)
    body_restock = r_restock.read().decode('utf-8')
    assert "restocked Product" in body_restock or "Procedure" in body_restock, "Restock procedure flash message missing"
    print("[OK] Manager POST /products/restock (Stored Procedure) - Success")

    # 5. Manager Execute Schema Alteration (Add Column)
    r_alter_get = opener.open(f"{BASE_URL}/schema-alter")
    csrf_alter = extract_csrf_token(r_alter_get.read().decode('utf-8'))
    alter_data = urllib.parse.urlencode({
        'csrf_token': csrf_alter,
        'operation': 'add_discount'
    }).encode('utf-8')
    r_alter = opener.open(f"{BASE_URL}/schema-alter", data=alter_data)
    body_alter = r_alter.read().decode('utf-8')
    assert "discount_pct" in body_alter, "Schema alteration failed to add discount_pct column"
    print("[OK] Manager POST /schema-alter (Pre-approved ALTER DDL) - Success")

    # 6. Logout Manager
    opener.open(f"{BASE_URL}/logout")
    print("[OK] GET /logout - Manager logged out")

    # 7. POST Login as Clerk
    clerk_cj = http.cookiejar.CookieJar()
    clerk_opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(clerk_cj))
    res_clerk_get = clerk_opener.open(f"{BASE_URL}/login")
    csrf_clerk = extract_csrf_token(res_clerk_get.read().decode('utf-8'))

    clerk_data = urllib.parse.urlencode({
        'csrf_token': csrf_clerk,
        'username': 'clerk_user',
        'password': 'clerk123'
    }).encode('utf-8')
    res_clerk = clerk_opener.open(f"{BASE_URL}/login", data=clerk_data)
    body_clerk = res_clerk.read().decode('utf-8')
    assert "CLERK" in body_clerk or "Welcome back" in body_clerk, "Clerk login failed"
    print("[OK] POST /login (clerk_user) - Success")

    # 8. Clerk Access Allowed Pages
    for path in ['/dashboard', '/products', '/orders', '/orders/place', '/reports', '/customers']:
        r = clerk_opener.open(f"{BASE_URL}{path}")
        assert r.status == 200, f"Clerk failed to access {path}"
        print(f"[OK] Clerk GET {path} - 200 OK")

    # 9. Clerk Access Restricted Pages (Must return HTTP 403 Forbidden)
    for path in ['/products/add', '/products/restock', '/schema-alter', '/admin/users', '/admin/audit-log', '/suppliers', '/brands']:
        try:
            clerk_opener.open(f"{BASE_URL}{path}")
            print(f"FAILED: Clerk was allowed access to restricted page {path}!")
            assert False
        except urllib.error.HTTPError as err:
            assert err.code == 403, f"Expected 403 Forbidden for {path}, got {err.code}"
            print(f"[OK] Clerk GET {path} - Correctly Blocked with HTTP 403 Forbidden")

    # 10. Test Trigger Stock Exception on Order Placement (Excess Stock Request)
    r_place_get = clerk_opener.open(f"{BASE_URL}/orders/place")
    csrf_order = extract_csrf_token(r_place_get.read().decode('utf-8'))

    order_data = urllib.parse.urlencode({
        'csrf_token': csrf_order,
        'customer_option': 'existing',
        'customer_id': '1',
        'payment_mode': 'UPI',
        'product_id[]': '1',
        'quantity[]': '999999'
    }).encode('utf-8')
    
    r_trigger = clerk_opener.open(f"{BASE_URL}/orders/place", data=order_data)
    body_trigger = r_trigger.read().decode('utf-8')
    assert "Insufficient stock" in body_trigger or "Rolled Back" in body_trigger, "Trigger error not captured in flash message"
    print("[OK] Clerk Order Placement with Excess Quantity - Trigger trg_check_stock caught & transaction rolled back!")

    # 11. Test Valid Order Placement by Clerk
    r_place_valid_get = clerk_opener.open(f"{BASE_URL}/orders/place")
    csrf_valid = extract_csrf_token(r_place_valid_get.read().decode('utf-8'))

    valid_order_data = urllib.parse.urlencode({
        'csrf_token': csrf_valid,
        'customer_option': 'existing',
        'customer_id': '1',
        'payment_mode': 'Cash',
        'product_id[]': '1',
        'quantity[]': '1'
    }).encode('utf-8')
    r_valid = clerk_opener.open(f"{BASE_URL}/orders/place", data=valid_order_data)
    body_valid = r_valid.read().decode('utf-8')
    assert "placed successfully" in body_valid or "INVOICE #" in body_valid, "Valid clerk order failed to complete"
    print("[OK] Clerk Valid Order Placement - Success & Invoice generated!")

    print("\nALL END-TO-END FLOW TESTS PASSED PERFECTLY!")

if __name__ == '__main__':
    run_tests()
