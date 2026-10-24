import os
import sys

# Ensure root directory is accessible in Python search path for Vercel Serverless Function
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from app import app

from urllib.parse import parse_qs, urlencode

class VercelPathFixer:
    """
    WSGI middleware to correct PATH_INFO when using Vercel rewrites.
    Vercel routes rewritten requests to /api/index?__vercel_route=/<path>.
    This middleware extracts the original route, sets PATH_INFO cleanly, and removes
    the routing query parameter so Flask blueprint routes match normally.
    """
    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        query_string = environ.get('QUERY_STRING', '')
        if '__vercel_route=' in query_string:
            params = parse_qs(query_string, keep_blank_values=True)
            if '__vercel_route' in params:
                raw_route = params.pop('__vercel_route')[0]
                environ['QUERY_STRING'] = urlencode(params, doseq=True)
                route = raw_route if raw_route.startswith('/') else '/' + raw_route
                # Handle root URL cleanly
                if not route:
                    route = '/'
                environ['PATH_INFO'] = route
                environ['SCRIPT_NAME'] = ''
        return self.wsgi_app(environ, start_response)

app.wsgi_app = VercelPathFixer(app.wsgi_app)

