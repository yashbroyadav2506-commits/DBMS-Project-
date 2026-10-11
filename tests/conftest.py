import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from app import app as flask_app
from config import Config
from db import get_db_cursor

@pytest.fixture
def app():
    flask_app.config.update({
        'TESTING': True,
        'WTF_CSRF_ENABLED': False,
        'DEBUG': False
    })
    yield flask_app

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def runner(app):
    return app.test_cli_runner()

def login_user(client, username, password):
    return client.post('/login', data={
        'username': username,
        'password': password
    }, follow_redirects=True)

def login_manager(client):
    return login_user(client, 'manager_user', 'manager123')

def login_clerk(client):
    return login_user(client, 'clerk_user', 'clerk123')
