"""
SecureLib - Application Entry Point
Initializes the Flask application instance and launches the development server.
"""

import os
from app import create_app, db

# Determine active environment configuration
env_name = os.getenv('FLASK_ENV', 'development')
app = create_app(env_name)

if __name__ == '__main__':
    with app.app_context():
        # Ensure database tables exist before starting
        db.create_all()

    # Launch server
    port = int(os.getenv('PORT', 5000))
    debug_mode = app.config.get('DEBUG', True)

    print("\n" + "=" * 65)
    print("   SECURELIB - CYBER SECURE LIBRARY MANAGEMENT SYSTEM")
    print("=" * 65)
    print(f" Environment : {env_name}")
    print(f" Server URL  : http://127.0.0.1:{port}")
    print(f" Debug Mode  : {debug_mode}")
    print("=" * 65 + "\n")

    app.run(host='127.0.0.1', port=port, debug=debug_mode)
