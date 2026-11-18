"""
Granthify - Vercel Serverless Function Entrypoint
Directly exposes the Flask application instance to Vercel's serverless WSGI runtime.
"""

import sys
import os

# Ensure the root project directory is in sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from run import app
