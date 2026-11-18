"""
SecureLib - Comprehensive Test Suite
Validates authentication, bcrypt hashing, brute-force lockout, RBAC, book circulation,
fine calculation, and SQL injection resilience.
"""

import pytest
from datetime import date, timedelta
from app import create_app, db
from app.models import User, Book, IssueRecord, Fine, ActivityLog, LoginAttempt


@pytest.fixture
def app():
    """Create and configure a clean testing app instance."""
    test_app = create_app('testing')
    with test_app.app_context():
        db.create_all()
        yield test_app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Testing client."""
    return app.test_client()


@pytest.fixture
def seed_test_users(app):
    """Seed test admin and test student accounts."""
    admin = User(
        username='test_admin',
        email='admin@test.com',
        full_name='Test Admin',
        role='admin',
        is_active=True
    )
    admin.set_password('AdminPass123!')

    student = User(
        username='test_student',
        email='student@test.com',
        full_name='Test Student',
        roll_number='23TEST01',
        role='student',
        is_active=True
    )
    student.set_password('StudentPass123!')

    db.session.add(admin)
    db.session.add(student)
    db.session.commit()
    return admin, student


# -------------------------------------------------------------
# 1. Authentication & Bcrypt Hashing Tests
# -------------------------------------------------------------

def test_password_hashing(app):
    """Verify that passwords are salted and hashed using bcrypt."""
    user = User(username='crypto_user', email='crypto@test.com', full_name='Crypto User', role='student')
    user.set_password('SecretP@ssword1')

    assert user.password_hash != 'SecretP@ssword1'
    assert user.password_hash.startswith('$2b$')  # Standard bcrypt prefix
    assert user.check_password('SecretP@ssword1') is True
    assert user.check_password('WrongPassword') is False


def test_account_lockout(app):
    """Verify that 5 failed attempts trigger an automatic temporary lockout."""
    user = User(username='brute_target', email='target@test.com', full_name='Target User', role='student')
    user.set_password('CorrectPass123!')
    db.session.add(user)
    db.session.commit()

    assert user.is_locked() is False
    assert user.failed_login_attempts == 0

    # Simulate 4 failed attempts
    for _ in range(4):
        user.record_failed_login(max_attempts=5, lockout_minutes=15)
        assert user.is_locked() is False

    # 5th failed attempt should trigger lockout
    user.record_failed_login(max_attempts=5, lockout_minutes=15)
    assert user.failed_login_attempts == 5
    assert user.is_locked() is True

    # Successful login or admin action resets lockout
    user.reset_failed_logins()
    assert user.failed_login_attempts == 0
    assert user.is_locked() is False


# -------------------------------------------------------------
# 2. Role-Based Access Control (RBAC) Tests
# -------------------------------------------------------------

def test_unauthenticated_access_blocked(client):
    """Unauthenticated users must not access protected admin or student routes."""
    res_admin = client.get('/admin/dashboard', follow_redirects=False)
    assert res_admin.status_code == 302  # Redirects to login

    res_student = client.get('/student/dashboard', follow_redirects=False)
    assert res_student.status_code == 302


def test_student_cannot_access_admin_portal(client, seed_test_users):
    """Students attempting to access /admin routes must receive 403 Forbidden."""
    # Log in as student
    client.post('/auth/login', data={'username': 'test_student', 'password': 'StudentPass123!'})

    # Attempt admin dashboard access
    res = client.get('/admin/dashboard')
    assert res.status_code == 403

    # Attempt book deletion
    res_delete = client.post('/admin/books/delete/1')
    assert res_delete.status_code == 403


def test_admin_cannot_access_student_portal(client, seed_test_users):
    """Administrators attempting student-specific actions receive 403 Forbidden."""
    client.post('/auth/login', data={'username': 'test_admin', 'password': 'AdminPass123!'})

    res = client.get('/student/dashboard')
    assert res.status_code == 403


def test_admin_can_access_admin_dashboard(client, seed_test_users):
    """Admin credentials allow authorized access to /admin/dashboard."""
    client.post('/auth/login', data={'username': 'test_admin', 'password': 'AdminPass123!'})
    res = client.get('/admin/dashboard')
    assert res.status_code == 200
    assert b'Administrative Operations' in res.data


# -------------------------------------------------------------
# 3. Book Inventory & Circulation Workflow Tests
# -------------------------------------------------------------

def test_book_issue_and_return_lifecycle(client, seed_test_users):
    """Test full cycle: add book -> student requests -> admin approves -> return book."""
    admin, student = seed_test_users

    # Admin adds book
    book = Book(
        title='Network Security Basics',
        author='Alice Smith',
        isbn='978-0111222333',
        category='Cyber Security',
        total_copies=2,
        available_copies=2
    )
    db.session.add(book)
    db.session.commit()

    assert book.available_copies == 2

    # Student logs in and requests book
    client.post('/auth/login', data={'username': 'test_student', 'password': 'StudentPass123!'})
    req_res = client.post(f'/student/request-book/{book.id}', follow_redirects=True)
    assert req_res.status_code == 200

    issue_rec = IssueRecord.query.filter_by(user_id=student.id, book_id=book.id).first()
    assert issue_rec is not None
    assert issue_rec.status == 'pending'

    # Admin logs in and approves request
    client.get('/auth/logout')
    client.post('/auth/login', data={'username': 'test_admin', 'password': 'AdminPass123!'})
    approve_res = client.post(f'/admin/issue/{issue_rec.id}/approve', follow_redirects=True)
    assert approve_res.status_code == 200

    db.session.refresh(book)
    db.session.refresh(issue_rec)
    assert issue_rec.status == 'issued'
    assert book.available_copies == 1  # Available copies decremented

    # Admin processes return
    return_res = client.post(f'/admin/issue/{issue_rec.id}/return', follow_redirects=True)
    assert return_res.status_code == 200

    db.session.refresh(book)
    db.session.refresh(issue_rec)
    assert issue_rec.status == 'returned'
    assert book.available_copies == 2  # Restored to 2 copies


# -------------------------------------------------------------
# 4. Overdue Fine Calculation Test
# -------------------------------------------------------------

def test_overdue_fine_calculation(app, seed_test_users):
    """Verify accurate fine calculation when a book is returned past its due date."""
    admin, student = seed_test_users

    book = Book(
        title='Malware Analysis',
        author='Bob Jones',
        isbn='978-9998887776',
        category='Cyber Security',
        total_copies=1,
        available_copies=0
    )
    db.session.add(book)
    db.session.commit()

    # Loan issued 20 days ago, due 6 days ago (14 days borrow period)
    issue_date = date.today() - timedelta(days=20)
    due_date = date.today() - timedelta(days=6)

    loan = IssueRecord(
        user_id=student.id,
        book_id=book.id,
        issue_date=issue_date,
        due_date=due_date,
        status='issued'
    )
    db.session.add(loan)
    db.session.commit()

    assert loan.is_overdue is True
    assert loan.overdue_days == 6
    assert loan.calculate_potential_fine(rate_per_day=5.0) == 30.0


# -------------------------------------------------------------
# 5. SQL Injection Immunity Test
# -------------------------------------------------------------

def test_sql_injection_resilience(client, seed_test_users):
    """Verify that common SQL injection payloads in search are safely escaped by ORM."""
    payloads = [
        "' OR '1'='1",
        "'; DROP TABLE books; --",
        "admin'--",
        "' UNION SELECT id, username, password_hash, 1, 1, 1, 1, 1, 1, 1, 1 FROM users--"
    ]

    for payload in payloads:
        res = client.get(f'/catalog?keyword={payload}')
        assert res.status_code == 200
        # Database tables must remain intact
        assert Book.query.count() >= 0
        assert User.query.count() == 2
