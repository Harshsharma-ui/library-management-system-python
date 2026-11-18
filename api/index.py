"""
Granthify - Vercel Serverless Function Entrypoint
Routes all incoming HTTP requests to the WSGI Flask application.
Employs VercelPathFixer to accurately extract the client URL path captured
by Vercel's rewrite rule (?__vercel_path=$1) so that all subroutes
(/auth/login, /catalog, /auth/register, etc.) navigate correctly without
returning 404 or getting stuck on the homepage.
"""

import sys
import os
from urllib.parse import parse_qs, urlencode
from werkzeug.middleware.proxy_fix import ProxyFix

# Ensure the root project directory is on sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from run import app


class VercelPathFixer:
    """
    WSGI Middleware for Vercel Serverless Functions.
    Accurately maps incoming request paths captured via Vercel's rewrite rule:
        {"source": "/(.*)", "destination": "/api/index?__vercel_path=$1"}
    Extracts __vercel_path, cleans it from QUERY_STRING, and assigns it to
    PATH_INFO so that Flask and all blueprints route cleanly.
    """
    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        qs = environ.get('QUERY_STRING', '')
        params = parse_qs(qs, keep_blank_values=True)

        if '__vercel_path' in params:
            # Extract the raw captured path parameter
            raw_path = params.pop('__vercel_path')[0]

            # Reconstruct clean QUERY_STRING without the internal __vercel_path
            clean_pairs = []
            for k, vs in params.items():
                for v in vs:
                    clean_pairs.append((k, v))
            environ['QUERY_STRING'] = urlencode(clean_pairs)

            # Clean and normalize PATH_INFO
            normalized_path = '/' + raw_path.lstrip('/')
            environ['PATH_INFO'] = normalized_path
            environ['SCRIPT_NAME'] = ''
        else:
            # Fallback for direct invocations or environments without the rewrite parameter
            path_info = environ.get('PATH_INFO', '')
            for prefix in ['/api/index.py', '/api/index']:
                if path_info == prefix or path_info == prefix + '/':
                    path_info = '/'
                    break
                elif path_info.startswith(prefix + '/'):
                    path_info = path_info[len(prefix):]
                    break
            environ['PATH_INFO'] = path_info or '/'
            environ['SCRIPT_NAME'] = ''

        # Reconstruct RAW_URI / REQUEST_URI for WSGI compliance
        clean_qs = environ.get('QUERY_STRING', '')
        raw_uri = environ['PATH_INFO'] + (('?' + clean_qs) if clean_qs else '')
        environ['RAW_URI'] = raw_uri
        environ['REQUEST_URI'] = raw_uri

        return self.wsgi_app(environ, start_response)


# Wrap with ProxyFix for HTTPS/X-Forwarded headers, then apply VercelPathFixer
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)
app.wsgi_app = VercelPathFixer(app.wsgi_app)
