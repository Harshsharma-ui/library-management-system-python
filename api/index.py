"""
Granthify - Vercel Serverless Function Entrypoint
Routes all incoming HTTP requests to the WSGI Flask application,
stripping serverless function route prefixes so all Flask routes resolve cleanly.
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
    WSGI Middleware to strip Vercel serverless function prefixes
    (/api/index, /api/index.py) from PATH_INFO so Flask routes match accurately.
    """
    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
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
