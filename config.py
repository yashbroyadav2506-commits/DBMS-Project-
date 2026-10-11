import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Environment Detection
    IS_VERCEL = bool(os.getenv('VERCEL'))
    IS_PRODUCTION = (
        os.getenv('FLASK_ENV') == 'production' or 
        IS_VERCEL or 
        os.getenv('ENV') == 'production'
    )

    # Security & Sessions
    # Fail fast if SECRET_KEY is missing in production / Vercel
    raw_secret = os.getenv('SECRET_KEY', '').strip()
    if not raw_secret:
        if IS_PRODUCTION:
            raise RuntimeError(
                "CRITICAL SECURITY CONFIGURATION ERROR: SECRET_KEY environment variable is missing! "
                "You must set a secure SECRET_KEY in your Vercel project environment variables."
            )
        SECRET_KEY = 'super-secret-grocery-db-key-2026-local-dev-only'
    else:
        SECRET_KEY = raw_secret

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SECURE = True if (IS_PRODUCTION or os.getenv('SESSION_COOKIE_SECURE', 'False').lower() in ('true', '1')) else False
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=60)
    
    # Google OAuth 2.0 / OpenID Connect
    GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID', '').strip()
    GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET', '').strip()
    GOOGLE_REDIRECT_URI = os.getenv('GOOGLE_REDIRECT_URI', 'http://localhost:5000/auth/google/callback').strip()
    GOOGLE_DISCOVERY_URL = 'https://accounts.google.com/.well-known/openid-configuration'
    
    # Access Control & Bootstrapping
    ALLOWED_EMAIL_DOMAINS = [d.strip().lower() for d in os.getenv('ALLOWED_EMAIL_DOMAINS', '').split(',') if d.strip()]
    INITIAL_MANAGER_EMAIL = os.getenv('INITIAL_MANAGER_EMAIL', '').strip().lower()
    
    # Database Settings (Serverless-Optimized)
    DB_HOST = os.getenv('DB_HOST', 'localhost').strip()
    DB_PORT = int(os.getenv('DB_PORT', 3306))
    DB_NAME = os.getenv('DB_NAME', 'grocery_shop_db').strip()
    # Serverless horizontal scaling requires a lean connection pool per lambda
    DB_POOL_SIZE = int(os.getenv('DB_POOL_SIZE', 2 if IS_VERCEL else 5))
    DB_CONNECT_TIMEOUT = int(os.getenv('DB_CONNECT_TIMEOUT', 10))
    DB_READ_TIMEOUT = int(os.getenv('DB_READ_TIMEOUT', 15))
    
    # SSL Configuration for Cloud Databases (Aiven, PlanetScale, TiDB, AWS RDS)
    DB_SSL_CA = os.getenv('DB_SSL_CA', '').strip()
    DB_SSL_MODE = os.getenv('DB_SSL_MODE', '').strip()
    DB_SSL_DISABLED = os.getenv('DB_SSL_DISABLED', 'False').lower() in ('true', '1')
    
    # Manager Credentials (Full DDL/DML access)
    MANAGER_DB_USER = os.getenv('MANAGER_DB_USER', 'shop_manager').strip()
    MANAGER_DB_PASS = os.getenv('MANAGER_DB_PASS', 'Manager@123').strip()
    
    # Clerk Credentials (Restricted access)
    CLERK_DB_USER = os.getenv('CLERK_DB_USER', 'shop_clerk').strip()
    CLERK_DB_PASS = os.getenv('CLERK_DB_PASS', 'Clerk@123').strip()
    
    # Caching & Rate Limiting (In-memory default, Redis URL optional)
    REDIS_URL = os.getenv('REDIS_URL', '').strip()
    if REDIS_URL:
        CACHE_TYPE = 'RedisCache'
        CACHE_REDIS_URL = REDIS_URL
        RATELIMIT_STORAGE_URI = REDIS_URL
    else:
        CACHE_TYPE = 'SimpleCache'
        RATELIMIT_STORAGE_URI = 'memory://'
        
    CACHE_DEFAULT_TIMEOUT = int(os.getenv('CACHE_DEFAULT_TIMEOUT', 60))
    RATELIMIT_STRATEGY = 'fixed-window'
    
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
