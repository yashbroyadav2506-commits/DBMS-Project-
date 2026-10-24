import os
import sys

# Ensure root directory is accessible in Python search path for Vercel Serverless Function
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from app import app

class VercelPathFixer:
    """
    WSGI middleware to correct PATH_INFO when using Vercel rewrites.
    Vercel routes rewritten requests to /api/index, setting PATH_INFO to '/api/index'.
    This middleware restores the original requested URI/path from Vercel headers.
    """
    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        matched_path = (
            environ.get('HTTP_X_VERCEL_MATCHED_PATH') or
            environ.get('HTTP_X_MATCHED_PATH') or
            environ.get('HTTP_X_FORWARDED_URI') or
            environ.get('REQUEST_URI')
        )
        if matched_path:
            path = matched_path.split('?')[0]
            if path and path != '/api/index':
                environ['PATH_INFO'] = path
                environ['SCRIPT_NAME'] = ''
        return self.wsgi_app(environ, start_response)

app.wsgi_app = VercelPathFixer(app.wsgi_app)

