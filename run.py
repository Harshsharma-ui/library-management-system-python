"""
Granthify - Application Entry Point & WSGI Handler
Initializes the Flask application instance and launches the server.
"""

import os
from app import create_app, db

# Determine active environment configuration
env_name = os.getenv('FLASK_ENV', 'production' if os.getenv('VERCEL') else 'development')
app = create_app(env_name)

# Ensure database tables exist and auto-seed when deploying to Vercel/serverless
with app.app_context():
    try:
        db.create_all()
        # If running on Vercel and database is empty, auto-seed demo data
        if os.getenv('VERCEL'):
            from app.models import User
            if User.query.count() == 0:
                from seed import seed_database
                seed_database(app)
    except Exception as e:
        print(f"[STARTUP NOTE] Database initialization: {e}")

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug_mode = app.config.get('DEBUG', True)

    print("\n" + "=" * 65)
    print("   GRANTHIFY - CYBER SECURE LIBRARY MANAGEMENT SYSTEM")
    print("=" * 65)
    print(f" Environment : {env_name}")
    print(f" Server URL  : http://127.0.0.1:{port}")
    print(f" Debug Mode  : {debug_mode}")
    print("=" * 65 + "\n")

    app.run(host='0.0.0.0', port=port, debug=debug_mode, use_reloader=False)
