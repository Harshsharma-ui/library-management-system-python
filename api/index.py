"""
Granthify - Vercel Serverless Function Entrypoint
Routes all incoming HTTP requests to the WSGI Flask application.
"""

import sys
import os

# Add root project directory to Python sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from run import app
