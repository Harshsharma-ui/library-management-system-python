"""
Granthify - Database Models
Defines relational models with constraints, relationships, and security helpers.
"""

from datetime import datetime, timezone, date, timedelta
from flask_login import UserMixin
from app import db, bcrypt


def get_utc_now():
    """Helper to return current timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


class User(UserMixin, db.Model):
    """User account model supporting Role-Based Access Control and brute-force lockout."""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='student')  # 'admin' or 'student'
    full_name = db.Column(db.String(100), nullable=False)
    roll_number = db.Column(db.String(30), unique=True, nullable=True)  # Required for students
    phone = db.Column(db.String(20), nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    # Brute-force protection fields
    failed_login_attempts = db.Column(db.Integer, default=0, nullable=False)
    locked_until = db.Column(db.DateTime, nullable=True)

    created_at = db.Column(db.DateTime, default=get_utc_now, nullable=False)

    # Relationships
    issue_records = db.relationship('IssueRecord', backref='student', lazy='dynamic',
                                    foreign_keys='IssueRecord.user_id', cascade='all, delete-orphan')
    fines = db.relationship('Fine', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    activity_logs = db.relationship('ActivityLog', backref='user', lazy='dynamic')

    def set_password(self, password):
        """Hash password using bcrypt with automatic salt generation (work factor 12)."""
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        """Verify plain password against bcrypt hash."""
        return bcrypt.check_password_hash(self.password_hash, password)

    def is_locked(self):
        """Check if user account is currently locked due to excessive failed logins."""
        if self.locked_until is None:
            return False
        # Normalize naive / aware comparison if needed
        now = datetime.now(timezone.utc)
        lock_time = self.locked_until
        if lock_time.tzinfo is None:
            lock_time = lock_time.replace(tzinfo=timezone.utc)
        return now < lock_time

    def record_failed_login(self, max_attempts=5, lockout_minutes=15):
        """Increment failed attempts and apply lockout when threshold is reached."""
        self.failed_login_attempts += 1
        if self.failed_login_attempts >= max_attempts:
            self.locked_until = datetime.now(timezone.utc) + timedelta(minutes=lockout_minutes)
        db.session.commit()

    def reset_failed_logins(self):
        """Reset failed attempt counters upon successful login or admin unlock."""
        self.failed_login_attempts = 0
        self.locked_until = None
        db.session.commit()

    @property
    def is_admin(self):
        """Check if user has administrative privileges."""
        return self.role == 'admin'

    def __repr__(self):
        return f"<User id={self.id} username='{self.username}' role='{self.role}'>"


class Book(db.Model):
    """Book model storing library catalog data and inventory counts."""
    __tablename__ = 'books'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False, index=True)
    author = db.Column(db.String(150), nullable=False, index=True)
    isbn = db.Column(db.String(20), unique=True, nullable=False, index=True)
    category = db.Column(db.String(100), nullable=False, index=True)
    total_copies = db.Column(db.Integer, default=1, nullable=False)
    available_copies = db.Column(db.Integer, default=1, nullable=False)
    shelf_location = db.Column(db.String(50), default='General', nullable=False)
    description = db.Column(db.Text, default='', nullable=True)
    created_at = db.Column(db.DateTime, default=get_utc_now, nullable=False)

    # Relationships
    issue_records = db.relationship('IssueRecord', backref='book', lazy='dynamic', cascade='all, delete-orphan')

    @property
    def is_available(self):
        """Return True if at least one physical copy is available for borrowing."""
        return self.available_copies > 0

    def __repr__(self):
        return f"<Book id={self.id} title='{self.title}' available={self.available_copies}/{self.total_copies}>"


class IssueRecord(db.Model):
    """Borrowing record tracking issue date, due date, return status, and fine linkage."""
    __tablename__ = 'issue_records'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    book_id = db.Column(db.Integer, db.ForeignKey('books.id'), nullable=False, index=True)
    issue_date = db.Column(db.Date, nullable=True)
    due_date = db.Column(db.Date, nullable=True)
    return_date = db.Column(db.Date, nullable=True)
    # Statuses: 'pending' (requested), 'issued', 'returned', 'rejected'
    status = db.Column(db.String(20), default='pending', nullable=False, index=True)
    issued_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    notes = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=get_utc_now, nullable=False)

    # Relationship to issuer user
    issued_by = db.relationship('User', foreign_keys=[issued_by_id])
    # Relationship to fine (if any)
    fine = db.relationship('Fine', backref='issue_record', uselist=False, cascade='all, delete-orphan')

    @property
    def is_overdue(self):
        """Check if an active book loan has exceeded its return due date."""
        if self.status == 'issued' and self.due_date:
            return date.today() > self.due_date
        return False

    @property
    def overdue_days(self):
        """Calculate overdue days."""
        if self.status == 'issued' and self.due_date and date.today() > self.due_date:
            return (date.today() - self.due_date).days
        if self.status == 'returned' and self.due_date and self.return_date and self.return_date > self.due_date:
            return (self.return_date - self.due_date).days
        return 0

    def calculate_potential_fine(self, rate_per_day=5.0):
        """Calculate fine based on days overdue and daily rate."""
        days = self.overdue_days
        return round(days * rate_per_day, 2) if days > 0 else 0.0

    def __repr__(self):
        return f"<IssueRecord id={self.id} user_id={self.user_id} book_id={self.book_id} status='{self.status}'>"


class Fine(db.Model):
    """Fine model recording overdue penalties and payment status."""
    __tablename__ = 'fines'

    id = db.Column(db.Integer, primary_key=True)
    issue_record_id = db.Column(db.Integer, db.ForeignKey('issue_records.id'), nullable=False, unique=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    amount = db.Column(db.Float, nullable=False, default=0.0)
    status = db.Column(db.String(20), default='unpaid', nullable=False, index=True)  # 'unpaid', 'paid'
    paid_date = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=get_utc_now, nullable=False)

    def __repr__(self):
        return f"<Fine id={self.id} user_id={self.user_id} amount={self.amount} status='{self.status}'>"


class ActivityLog(db.Model):
    """Security audit log tracking sensitive actions, IP addresses, and user activities."""
    __tablename__ = 'activity_logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)
    username = db.Column(db.String(50), nullable=True)
    action = db.Column(db.String(100), nullable=False, index=True)
    ip_address = db.Column(db.String(45), nullable=False)
    details = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=get_utc_now, nullable=False, index=True)

    def __repr__(self):
        return f"<ActivityLog id={self.id} action='{self.action}' ip='{self.ip_address}'>"


class LoginAttempt(db.Model):
    """Audit table logging authentication attempts for intrusion detection and rate monitoring."""
    __tablename__ = 'login_attempts'

    id = db.Column(db.Integer, primary_key=True)
    ip_address = db.Column(db.String(45), nullable=False, index=True)
    username = db.Column(db.String(50), nullable=False, index=True)
    success = db.Column(db.Boolean, nullable=False)
    timestamp = db.Column(db.DateTime, default=get_utc_now, nullable=False, index=True)

    def __repr__(self):
        return f"<LoginAttempt user='{self.username}' success={self.success} ip='{self.ip_address}'>"
