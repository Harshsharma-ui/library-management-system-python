"""
Granthify - Vercel Serverless Function Entrypoint
Routes all incoming HTTP requests to the WSGI Flask application,
restoring the original requested path from Vercel's X-Matched-Path header.
"""

import sys
import os

# Add root project directory to Python sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from run import app


class VercelPathMiddleware:
    """
    WSGI Middleware to restore the original request path from Vercel's
    HTTP_X_MATCHED_PATH header before rewrites redirected it to /api/index.
    """
    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        # When Vercel rewrites requests to /api/index, the original path requested
        # by the browser is stored in HTTP_X_MATCHED_PATH (or HTTP_X_FORWARDED_PATH).
        matched_path = environ.get('HTTP_X_MATCHED_PATH') or environ.get('HTTP_X_FORWARDED_PATH')
        if matched_path:
            # Strip query string if present in matched_path (Flask reads QUERY_STRING separately)
            path_only = matched_path.split('?')[0]
            # Strip /api/index prefix if it was prepended
            for prefix in ['/api/index.py', '/api/index']:
                if path_only == prefix or path_only == prefix + '/':
                    path_only = '/'
                    break
                elif path_only.startswith(prefix + '/'):
                    path_only = path_only[len(prefix):]
                    break
            environ['PATH_INFO'] = path_only or '/'
        else:
            path = environ.get('PATH_INFO', '')
            for prefix in ['/api/index.py', '/api/index']:
                if path == prefix or path == prefix + '/':
                    environ['PATH_INFO'] = '/'
                    break
                elif path.startswith(prefix + '/'):
                    environ['PATH_INFO'] = path[len(prefix):]
                    break
        return self.wsgi_app(environ, start_response)


# Wrap Flask's WSGI application with the path normalizer
app.wsgi_app = VercelPathMiddleware(app.wsgi_app)
