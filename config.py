"""
Granthify - Configuration Module
Defines environment-based configuration settings with security hardening.
"""

import os
from datetime import timedelta
from dotenv import load_dotenv

# Base directory of the application
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# Load environment variables from .env file
load_dotenv(os.path.join(BASE_DIR, '.env'))


class Config:
    """Base configuration with security best practices."""

    # Cryptographic Secret Key for sessions and CSRF protection
    SECRET_KEY = os.getenv('SECRET_KEY', 'default-dev-secret-key-change-in-production')

    # Database Configuration
    SQLALCHEMY_DATABASE_URI = os.getenv(
        'DATABASE_URL',
        f"sqlite:///{os.path.join(BASE_DIR, 'granthify.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Security: Session Cookie Hardening
    # HTTPOnly prevents JavaScript from reading session cookies (Mitigates XSS-based session hijacking)
    SESSION_COOKIE_HTTPONLY = True
    # SameSite='Lax' ensures cookies are not sent on cross-site subrequests (Mitigates CSRF)
    SESSION_COOKIE_SAMESITE = 'Lax'
    # In production with HTTPS, this should be True. In development (HTTP), keep False.
    SESSION_COOKIE_SECURE = False
    # Session lifespan
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=60)

    # CSRF Protection
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600  # CSRF token valid for 1 hour

    # Business Rules
    DAILY_FINE_RATE = float(os.getenv('DAILY_FINE_RATE', 5.0))  # Currency units per overdue day
    BORROW_DURATION_DAYS = int(os.getenv('BORROW_DURATION_DAYS', 14))  # Standard book loan period
    MAX_BORROW_LIMIT = int(os.getenv('MAX_BORROW_LIMIT', 3))  # Max active books per student
    MAX_LOGIN_ATTEMPTS = int(os.getenv('MAX_LOGIN_ATTEMPTS', 5))  # Lock account after 5 failed attempts
    LOCKOUT_DURATION_MINUTES = int(os.getenv('LOCKOUT_DURATION_MINUTES', 15))  # Lockout window


class DevelopmentConfig(Config):
    """Development configuration with debugging enabled."""
    DEBUG = True
    ENV = 'development'


class TestingConfig(Config):
    """Testing configuration with in-memory SQLite and disabled CSRF."""
    TESTING = True
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    LOGIN_DISABLED = False


class ProductionConfig(Config):
    """Production configuration with strict security flags."""
    DEBUG = False
    TESTING = False
    SESSION_COOKIE_SECURE = True  # Requires HTTPS


# Configuration dictionary for factory setup
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
