"""
Granthify - Vercel Serverless Function Entrypoint
Routes all incoming HTTP requests to the WSGI Flask application.
Employs VercelPathFixer to extract the browser's true REQUEST_URI so that
all sub-routes (/auth/login, /catalog, /auth/register, /static/...) resolve cleanly.
"""

import sys
import os

# Ensure the root project directory is on sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from run import app


class VercelPathFixer:
    """
    WSGI Middleware for Vercel Serverless Functions.
    Resolves the original request path from REQUEST_URI / RAW_URI and
    resets SCRIPT_NAME and PATH_INFO so Flask routes and Blueprints match.
    """
    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        # Retrieve the original URI requested by the client browser
        raw_uri = (
            environ.get('REQUEST_URI') or
            environ.get('RAW_URI') or
            environ.get('HTTP_X_FORWARDED_PATH') or
            environ.get('PATH_INFO', '')
        )
        if raw_uri:
            # Strip query string parameters if present
            path_only = raw_uri.split('?')[0]

            # If the path has the /api/index serverless prefix, strip it
            for prefix in ['/api/index.py', '/api/index']:
                if path_only == prefix or path_only == prefix + '/':
                    path_only = '/'
                    break
                elif path_only.startswith(prefix + '/'):
                    path_only = path_only[len(prefix):]
                    break

            environ['PATH_INFO'] = path_only or '/'
            environ['SCRIPT_NAME'] = ''

        return self.wsgi_app(environ, start_response)


# Apply the Vercel path fixer middleware to Flask's WSGI callable
app.wsgi_app = VercelPathFixer(app.wsgi_app)
