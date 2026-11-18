"""
Granthify - Application Factory & Extension Initialization
Initializes Flask extensions, registers blueprints, and sets up custom error handlers.
"""

from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_bcrypt import Bcrypt
from flask_wtf.csrf import CSRFProtect

from config import config

# Initialize Flask extensions
db = SQLAlchemy()
bcrypt = Bcrypt()
login_manager = LoginManager()
csrf = CSRFProtect()

# Configure Flask-Login settings
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'warning'


def create_app(config_name='default'):
    """Application factory function."""
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # Initialize extensions with app context
    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    # Register blueprints
    from app.routes.main import main_bp
    from app.routes.auth import auth_bp
    from app.routes.admin import admin_bp
    from app.routes.student import student_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(student_bp, url_prefix='/student')

    # Register custom error handlers (Cybersecurity feature: Prevent information disclosure)
    register_error_handlers(app)

    # User loader callback for Flask-Login
    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    return app


def register_error_handlers(app):
    """Custom error handlers to avoid exposing stack traces or DB errors to users."""

    @app.errorhandler(403)
    def forbidden_error(error):
        return render_template('403.html'), 403

    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()  # Rollback transaction to avoid corrupted session
        return render_template('500.html'), 500
