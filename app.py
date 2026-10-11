import time
from flask import Flask, render_template, request, session, jsonify
from flask_wtf.csrf import CSRFProtect
from werkzeug.middleware.proxy_fix import ProxyFix
from config import Config
from db import close_db, DatabaseUnreachableError
from logger import logger
from services.oauth_service import init_oauth

from blueprints.auth import auth_bp
from blueprints.dashboard import dashboard_bp
from blueprints.products import products_bp
from blueprints.orders import orders_bp
from blueprints.customers import customers_bp
from blueprints.suppliers_brands import suppliers_brands_bp
from blueprints.reports import reports_bp
from blueprints.admin import admin_bp
from blueprints.schema_alter import schema_alter_bp

# Expose WSGI application object at the module level for Vercel and local dev
app = Flask(__name__, static_folder='public', static_url_path='/static')
app.config.from_object(Config)

# Apply ProxyFix so that https scheme, client IP, and host headers are resolved accurately behind reverse proxies (Vercel)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

# Enable CSRF Protection on all POST requests
csrf = CSRFProtect(app)

# Initialize Authlib Google OAuth 2.0 / OpenID Connect
init_oauth(app)

# Context processor for dynamic navbar data (e.g. pending access requests badge for managers)
@app.context_processor
def inject_navbar_data():
    pending_count = 0
    if session.get('role') == 'manager':
        try:
            from services.admin_service import get_pending_requests_count
            pending_count = get_pending_requests_count()
        except Exception:
            pending_count = 0
    return {
        'pending_requests_count': pending_count
    }

# Register Blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(dashboard_bp)
app.register_blueprint(products_bp)
app.register_blueprint(orders_bp)
app.register_blueprint(customers_bp)
app.register_blueprint(suppliers_brands_bp)
app.register_blueprint(reports_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(schema_alter_bp)

# Register Database Teardown
app.teardown_appcontext(close_db)

# ----------------- HEALTH CHECK ROUTE -----------------
@app.route('/health')
def health_check():
    """
    Health check endpoint for Vercel, uptime monitors, and container orchestrators.
    Verifies MySQL connectivity by executing a lightweight SELECT 1.
    """
    try:
        from db import get_db_cursor
        with get_db_cursor('manager') as (conn, cursor):
            cursor.execute("SELECT 1 AS alive;")
            row = cursor.fetchone()
            db_alive = bool(row and (row.get('alive') == 1 or row.get('1') == 1))
        
        return jsonify({
            'status': 'healthy',
            'database': 'connected' if db_alive else 'unknown',
            'database_name': Config.DB_NAME,
            'database_host': Config.DB_HOST,
            'timestamp': int(time.time())
        }), 200
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            'status': 'unhealthy',
            'database': 'disconnected',
            'database_host': Config.DB_HOST,
            'error': str(e),
            'timestamp': int(time.time())
        }), 503

# ----------------- ERROR HANDLERS -----------------
@app.errorhandler(DatabaseUnreachableError)
def db_unreachable_error(error):
    logger.critical(f"Database Unreachable Error on {request.path}: {error}")
    return render_template(
        '500.html',
        title="503 Service Unavailable - Database Unreachable",
        message="Unable to connect to the MySQL database server. If deploying to Vercel, verify your cloud DB host, port, credentials, and SSL settings in your Vercel Environment Variables."
    ), 503

@app.errorhandler(403)
def forbidden_error(error):
    logger.warning(f"403 Forbidden on {request.path} from IP {request.remote_addr}")
    return render_template('403.html', title="403 Forbidden"), 403

@app.errorhandler(404)
def not_found_error(error):
    logger.info(f"404 Not Found: {request.path}")
    return render_template('404.html', title="404 Not Found"), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"500 Internal Server Error on {request.path}: {error}", exc_info=True)
    return render_template('500.html', title="500 Server Error"), 500

@app.errorhandler(400)
def bad_request_error(error):
    logger.warning(f"400 Bad Request on {request.path}: {error}")
    return render_template('500.html', title="400 Bad Request", message="Invalid request or CSRF token validation failed."), 400

if __name__ == '__main__':
    logger.info("Starting Grocery Store DBMS Application on http://127.0.0.1:5000")
    print("Starting Grocery Store DBMS Application on http://127.0.0.1:5000")
    app.run(host='127.0.0.1', port=5000, debug=True)
