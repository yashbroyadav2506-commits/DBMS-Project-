"""
OAuth and OpenID Connect Service using Authlib.
Configures Google OAuth 2.0 client with OpenID Connect discovery.
"""
from typing import Optional, Dict, Any
from flask import current_app
from authlib.integrations.flask_client import OAuth
from logger import logger

oauth = OAuth()

def init_oauth(app) -> OAuth:
    """
    Initializes OAuth with the Flask application context.
    """
    oauth.init_app(app)
    
    client_id = app.config.get('GOOGLE_CLIENT_ID', '')
    client_secret = app.config.get('GOOGLE_CLIENT_SECRET', '')
    discovery_url = app.config.get(
        'GOOGLE_DISCOVERY_URL',
        'https://accounts.google.com/.well-known/openid-configuration'
    )
    
    oauth.register(
        name='google',
        client_id=client_id,
        client_secret=client_secret,
        server_metadata_url=discovery_url,
        client_kwargs={
            'scope': 'openid email profile'
        }
    )
    logger.info("Authlib Google OAuth OpenID Connect client registered.")
    return oauth

def is_google_oauth_configured() -> bool:
    """
    Checks if Google Client ID and Secret have been configured in environment.
    """
    try:
        cfg = current_app.config
        cid = cfg.get('GOOGLE_CLIENT_ID', '').strip()
        sec = cfg.get('GOOGLE_CLIENT_SECRET', '').strip()
        return bool(cid and sec and cid != 'your-google-client-id.apps.googleusercontent.com')
    except Exception:
        return False
