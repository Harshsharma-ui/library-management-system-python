"""
Granthify - Utility Functions
Security helpers, IP detection, audit logging, and fine calculations.
"""

import re
from datetime import date, datetime, timezone
from flask import request, current_app
from flask_login import current_user
from app import db
from app.models import ActivityLog, LoginAttempt, IssueRecord, Fine


def get_client_ip():
    """
    Safely retrieve client IP address, handling reverse proxies.
    Validates formatting to prevent spoofed header injection.
    """
    if request.headers.get('X-Forwarded-For'):
        # In a multi-proxy chain, the first IP is the original client
        ip = request.headers.get('X-Forwarded-For').split(',')[0].strip()
    else:
        ip = request.remote_addr or '127.0.0.1'

    # Basic regex validation for IPv4 or IPv6
    ipv4_pattern = r'^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$'
    ipv6_pattern = r'^[0-9a-fA-F:]+$'
    if re.match(ipv4_pattern, ip) or re.match(ipv6_pattern, ip):
        return ip
    return '127.0.0.1'


def log_activity(action, details, user_id=None, username=None):
    """
    Record an administrative or student action into the security audit log.
    Captures user identity, action description, timestamp, and client IP.
    """
    try:
        ip = get_client_ip()
        uid = user_id
        uname = username

        if uid is None and current_user and current_user.is_authenticated:
            uid = current_user.id
            uname = current_user.username
        elif uname is None and uid:
            from app.models import User
            user = db.session.get(User, uid)
            if user:
                uname = user.username

        log_entry = ActivityLog(
            user_id=uid,
            username=uname or 'Anonymous/System',
            action=action,
            ip_address=ip,
            details=details
        )
        db.session.add(log_entry)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        # Fallback print to prevent logging failure from crashing the app
        print(f"[AUDIT LOG ERROR] Failed to record log: {e}")


def record_login_attempt(username, success):
    """
    Record authentication attempts into login_attempts table for intrusion detection.
    """
    try:
        ip = get_client_ip()
        attempt = LoginAttempt(
            ip_address=ip,
            username=username[:50] if username else 'unknown',
            success=success
        )
        db.session.add(attempt)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"[LOGIN ATTEMPT LOG ERROR] Failed to record attempt: {e}")


def sanitize_input(text):
    """
    Basic input sanitization stripping risky HTML/JavaScript tags to mitigate XSS attacks.
    """
    if not isinstance(text, str):
        return text
    # Strip HTML tags
    clean = re.sub(r'<[^>]*?>', '', text)
    # Strip dangerous script triggers
    clean = re.sub(r'(javascript:|onload=|onclick=|onerror=)', '', clean, flags=re.IGNORECASE)
    return clean.strip()


def sync_overdue_fines():
    """
    Scan all active issued records, calculate any accrued fines for overdue books,
    and update or create entries in the fines table.
    """
    daily_rate = current_app.config.get('DAILY_FINE_RATE', 5.0)
    today = date.today()

    # Query all records currently in 'issued' state with due_date < today
    overdue_issues = IssueRecord.query.filter(
        IssueRecord.status == 'issued',
        IssueRecord.due_date < today
    ).all()

    updates_count = 0
    for issue in overdue_issues:
        days_late = (today - issue.due_date).days
        if days_late > 0:
            fine_amount = round(days_late * daily_rate, 2)
            existing_fine = Fine.query.filter_by(issue_record_id=issue.id).first()
            if existing_fine:
                if existing_fine.status == 'unpaid' and existing_fine.amount != fine_amount:
                    existing_fine.amount = fine_amount
                    updates_count += 1
            else:
                new_fine = Fine(
                    issue_record_id=issue.id,
                    user_id=issue.user_id,
                    amount=fine_amount,
                    status='unpaid'
                )
                db.session.add(new_fine)
                updates_count += 1

    if updates_count > 0:
        db.session.commit()
    return updates_count
