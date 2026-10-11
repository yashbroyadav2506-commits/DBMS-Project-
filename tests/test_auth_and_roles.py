from tests.conftest import login_manager, login_clerk

def test_manager_login_success(client):
    res = login_manager(client)
    assert res.status_code == 200
    assert b"MANAGER" in res.data or b"Dashboard" in res.data

def test_clerk_login_success(client):
    res = login_clerk(client)
    assert res.status_code == 200
    assert b"CLERK" in res.data or b"Dashboard" in res.data

def test_invalid_login_rejected(client):
    res = client.post('/login', data={'username': 'manager_user', 'password': 'wrongpassword'}, follow_redirects=True)
    assert res.status_code == 200
    assert b"Invalid username or password" in res.data

def test_manager_access_granted(client):
    login_manager(client)
    for path in ['/dashboard', '/products', '/products/add', '/products/restock', '/schema-alter', '/admin/users', '/admin/audit-log']:
        res = client.get(path)
        assert res.status_code == 200, f"Manager failed to access {path}"

def test_clerk_allowed_routes(client):
    login_clerk(client)
    for path in ['/dashboard', '/products', '/orders', '/reports', '/customers']:
        res = client.get(path)
        assert res.status_code == 200, f"Clerk failed to access allowed route {path}"

def test_clerk_blocked_from_manager_routes(client):
    login_clerk(client)
    for path in ['/products/add', '/products/restock', '/schema-alter', '/admin/users', '/admin/audit-log', '/suppliers', '/brands']:
        res = client.get(path)
        assert res.status_code == 403, f"Expected 403 Forbidden for clerk on {path}, got {res.status_code}"

def test_logout(client):
    login_manager(client)
    res = client.get('/logout', follow_redirects=True)
    assert res.status_code == 200
    assert b"logged out" in res.data.lower()

def test_health_check_endpoint(client):
    res = client.get('/health')
    assert res.status_code == 200
    data = res.get_json()
    assert data['status'] == 'healthy'
    assert data['database'] == 'connected'
    assert 'timestamp' in data
