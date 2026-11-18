"""
Granthify - Access Control Decorators
Enforces Role-Based Access Control (RBAC) and account status validation.
"""

from functools import wraps
from flask import abort, flash, redirect, url_for
from flask_login import current_user, logout_user


def admin_required(f):
    """Decorator to restrict view access strictly to users with the 'admin' role."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        if not current_user.is_active:
            logout_user()
            flash('Your account has been deactivated. Please contact the administrator.', 'danger')
            return redirect(url_for('auth.login'))
        if current_user.role != 'admin':
            # Abort with 403 Forbidden - do not leak sensitive administrative routes
            abort(403)
        return f(*args, **kwargs)
    return decorated_function


def student_required(f):
    """Decorator to restrict view access strictly to users with the 'student' role."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        if not current_user.is_active:
            logout_user()
            flash('Your account has been deactivated. Please contact the administrator.', 'danger')
            return redirect(url_for('auth.login'))
        if current_user.role != 'student':
            abort(403)
        return f(*args, **kwargs)
    return decorated_function


def active_user_required(f):
    """Decorator to verify that an authenticated user account is in an active state."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        if not current_user.is_active:
            logout_user()
            flash('Your account is deactivated. Please contact library support.', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function
