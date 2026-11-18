"""
Granthify - Authentication Blueprint
Handles login, registration, session management, logout, and password updates
with brute-force lockout, bcrypt hashing, and audit trails.
"""

from datetime import datetime, timezone
from flask import Blueprint, render_template, redirect, url_for, flash, request, session, current_app
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from app.models import User
from app.forms import LoginForm, StudentRegistrationForm, ChangePasswordForm
from app.utils import log_activity, record_login_attempt, sanitize_input

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """
    Authenticate users with brute-force defense, rate limiting, and session regeneration.
    """
    if current_user.is_authenticated:
        if current_user.role == 'admin':
            return redirect(url_for('admin.dashboard'))
        return redirect(url_for('student.dashboard'))

    form = LoginForm()
    if form.validate_on_submit():
        identifier = sanitize_input(form.username.data.strip())
        password = form.password.data

        # Allow login via username or email using SQLAlchemy ORM (SQL Injection safe)
        user = User.query.filter(
            (User.username == identifier) | (User.email == identifier.lower())
        ).first()

        max_attempts = current_app.config.get('MAX_LOGIN_ATTEMPTS', 5)
        lockout_minutes = current_app.config.get('LOCKOUT_DURATION_MINUTES', 15)

        if user:
            # 1. Check if user is currently locked out
            if user.is_locked():
                now = datetime.now(timezone.utc)
                lock_time = user.locked_until
                if lock_time.tzinfo is None:
                    lock_time = lock_time.replace(tzinfo=timezone.utc)
                remaining_minutes = max(1, int((lock_time - now).total_seconds() / 60) + 1)

                record_login_attempt(user.username, success=False)
                log_activity(
                    action='LOGIN_BLOCKED_LOCKOUT',
                    details=f'Login blocked for locked account. Remaining time: {remaining_minutes} min.',
                    user_id=user.id,
                    username=user.username
                )
                flash(
                    f'Account is temporarily locked due to multiple failed attempts. '
                    f'Please retry in {remaining_minutes} minute(s) or contact an administrator.',
                    'danger'
                )
                return render_template('auth/login.html', form=form)

            # 2. Check if account is active
            if not user.is_active:
                record_login_attempt(user.username, success=False)
                log_activity(
                    action='LOGIN_BLOCKED_INACTIVE',
                    details='Deactivated account attempted login.',
                    user_id=user.id,
                    username=user.username
                )
                flash('This account has been deactivated. Please contact the library administration.', 'danger')
                return render_template('auth/login.html', form=form)

            # 3. Verify password with bcrypt
            if user.check_password(password):
                # Reset lockout counter on success
                user.reset_failed_logins()

                # Cybersecurity: Session fixation defense - reset session identifier
                session.clear()

                login_user(user, remember=form.remember_me.data)

                record_login_attempt(user.username, success=True)
                log_activity(
                    action='LOGIN_SUCCESS',
                    details=f'User successfully authenticated as role: {user.role}.',
                    user_id=user.id,
                    username=user.username
                )

                flash(f'Welcome back, {user.full_name}!', 'success')

                # Handle safe redirection (Open Redirect vulnerability prevention)
                next_page = request.args.get('next')
                if next_page and next_page.startswith('/'):
                    return redirect(next_page)

                if user.role == 'admin':
                    return redirect(url_for('admin.dashboard'))
                return redirect(url_for('student.dashboard'))
            else:
                # Password incorrect - increment failed attempts
                user.record_failed_login(max_attempts=max_attempts, lockout_minutes=lockout_minutes)
                record_login_attempt(user.username, success=False)

                if user.is_locked():
                    log_activity(
                        action='ACCOUNT_LOCKED',
                        details=f'Account locked for {lockout_minutes} mins after {max_attempts} failed attempts.',
                        user_id=user.id,
                        username=user.username
                    )
                    flash(
                        f'Account locked! Too many failed attempts. Try again in {lockout_minutes} minutes.',
                        'danger'
                    )
                else:
                    remaining = max_attempts - user.failed_login_attempts
                    log_activity(
                        action='LOGIN_FAILED',
                        details=f'Bad password attempt. Attempts remaining: {remaining}.',
                        user_id=user.id,
                        username=user.username
                    )
                    flash(f'Invalid credentials. {remaining} attempt(s) remaining before temporary lockout.', 'warning')
        else:
            # User not found
            record_login_attempt(identifier, success=False)
            log_activity(
                action='LOGIN_FAILED_UNKNOWN_USER',
                details=f"Attempted login with non-existent username/email: '{identifier}'.",
                user_id=None,
                username=identifier
            )
            flash('Invalid username or password.', 'danger')

    return render_template('auth/login.html', form=form)


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """
    Register new student account with validated details and bcrypt hashed credentials.
    """
    if current_user.is_authenticated:
        return redirect(url_for('student.dashboard'))

    form = StudentRegistrationForm()
    if form.validate_on_submit():
        user = User(
            username=sanitize_input(form.username.data.strip()),
            email=form.email.data.strip().lower(),
            full_name=sanitize_input(form.full_name.data.strip()),
            roll_number=form.roll_number.data.strip().upper(),
            phone=form.phone.data.strip() if form.phone.data else None,
            role='student',
            is_active=True
        )
        user.set_password(form.password.data)

        db.session.add(user)
        db.session.commit()

        log_activity(
            action='STUDENT_REGISTER',
            details=f"Student registered. Roll: {user.roll_number}, Email: {user.email}",
            user_id=user.id,
            username=user.username
        )

        flash('Registration successful! You can now log in to access the library.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/register.html', form=form)


@auth_bp.route('/logout')
@login_required
def logout():
    """Securely terminate session and log the event."""
    log_activity(
        action='LOGOUT',
        details='User logged out.',
        user_id=current_user.id,
        username=current_user.username
    )
    logout_user()
    session.clear()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    """Allow an authenticated user to change their password securely."""
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if current_user.check_password(form.current_password.data):
            current_user.set_password(form.new_password.data)
            db.session.commit()

            log_activity(
                action='PASSWORD_CHANGED',
                details='User successfully updated account password.',
                user_id=current_user.id,
                username=current_user.username
            )
            flash('Your password has been changed successfully.', 'success')
            if current_user.role == 'admin':
                return redirect(url_for('admin.dashboard'))
            return redirect(url_for('student.dashboard'))
        else:
            flash('Incorrect current password. Please try again.', 'danger')

    return render_template('auth/change_password.html', form=form)
