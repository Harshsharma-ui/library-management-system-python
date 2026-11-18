"""
SecureLib - Admin Blueprint
Administrative controls: book inventory, student management, direct issues & approvals,
returns, fine enforcement, and security audit log analysis.
"""

from datetime import date, timedelta, datetime, timezone
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from sqlalchemy import func
from app import db
from app.models import User, Book, IssueRecord, Fine, ActivityLog, LoginAttempt
from app.forms import BookForm, DirectIssueForm
from app.decorators import admin_required
from app.utils import log_activity, sync_overdue_fines, sanitize_input

admin_bp = Blueprint('admin', __name__)


@admin_bp.before_request
@login_required
@admin_required
def enforce_admin_security():
    """Double-guard ensuring only authenticated active administrators reach admin endpoints."""
    pass


@admin_bp.route('/dashboard')
def dashboard():
    """Main administrative dashboard displaying system-wide analytics, alerts, and logs."""
    # Run fine synchronizer so stats reflect fresh overdue calculations
    sync_overdue_fines()

    today = date.today()

    # Aggregate Statistics
    total_books = db.session.query(func.coalesce(func.sum(Book.total_copies), 0)).scalar()
    total_titles = Book.query.count()
    available_copies = db.session.query(func.coalesce(func.sum(Book.available_copies), 0)).scalar()
    issued_books_count = IssueRecord.query.filter_by(status='issued').count()
    pending_requests_count = IssueRecord.query.filter_by(status='pending').count()
    total_students = User.query.filter_by(role='student').count()

    # Overdue issues count
    overdue_issues_count = IssueRecord.query.filter(
        IssueRecord.status == 'issued',
        IssueRecord.due_date < today
    ).count()

    # Total fines calculation
    unpaid_fines_total = db.session.query(
        func.coalesce(func.sum(Fine.amount), 0.0)
    ).filter_by(status='unpaid').scalar()

    collected_fines_total = db.session.query(
        func.coalesce(func.sum(Fine.amount), 0.0)
    ).filter_by(status='paid').scalar()

    # Overdue records list
    overdue_records = IssueRecord.query.filter(
        IssueRecord.status == 'issued',
        IssueRecord.due_date < today
    ).order_by(IssueRecord.due_date.asc()).limit(8).all()

    # Recent Audit Logs & Login Attempts
    recent_logs = ActivityLog.query.order_by(ActivityLog.timestamp.desc()).limit(7).all()
    recent_logins = LoginAttempt.query.order_by(LoginAttempt.timestamp.desc()).limit(6).all()

    return render_template(
        'admin/dashboard.html',
        total_books=total_books,
        total_titles=total_titles,
        available_copies=available_copies,
        issued_books_count=issued_books_count,
        pending_requests_count=pending_requests_count,
        total_students=total_students,
        overdue_issues_count=overdue_issues_count,
        unpaid_fines_total=round(unpaid_fines_total, 2),
        collected_fines_total=round(collected_fines_total, 2),
        overdue_records=overdue_records,
        recent_logs=recent_logs,
        recent_logins=recent_logins,
        today=today
    )


# ---------------------------------------------------------
# Book Inventory Management
# ---------------------------------------------------------

@admin_bp.route('/books')
def books():
    """List and search library book inventory."""
    search_query = request.args.get('search', '').strip()
    category_filter = request.args.get('category', '').strip()

    query = Book.query
    if search_query:
        pattern = f"%{search_query}%"
        query = query.filter(
            (Book.title.ilike(pattern)) |
            (Book.author.ilike(pattern)) |
            (Book.isbn.ilike(pattern))
        )
    if category_filter:
        query = query.filter(Book.category == category_filter)

    book_list = query.order_by(Book.title.asc()).all()

    # Distinct categories for filter dropdown
    categories = [r[0] for r in db.session.query(Book.category).distinct().all()]

    return render_template(
        'admin/books.html',
        books=book_list,
        search_query=search_query,
        category_filter=category_filter,
        categories=categories
    )


@admin_bp.route('/books/add', methods=['GET', 'POST'])
def add_book():
    """Add a new book title to the catalog."""
    form = BookForm()
    if form.validate_on_submit():
        isbn = form.isbn.data.strip()
        existing = Book.query.filter_by(isbn=isbn).first()
        if existing:
            flash(f'A book with ISBN {isbn} already exists in the catalog: "{existing.title}".', 'danger')
            return render_template('admin/book_form.html', form=form, title='Add New Book')

        new_book = Book(
            title=sanitize_input(form.title.data.strip()),
            author=sanitize_input(form.author.data.strip()),
            isbn=isbn,
            category=form.category.data,
            total_copies=form.total_copies.data,
            available_copies=form.total_copies.data,  # Initially all copies available
            shelf_location=sanitize_input(form.shelf_location.data.strip()) if form.shelf_location.data else 'General',
            description=sanitize_input(form.description.data.strip()) if form.description.data else ''
        )
        db.session.add(new_book)
        db.session.commit()

        log_activity(
            action='BOOK_ADDED',
            details=f"Added book '{new_book.title}' (ISBN: {new_book.isbn}, Copies: {new_book.total_copies})."
        )
        flash(f'Book "{new_book.title}" added successfully!', 'success')
        return redirect(url_for('admin.books'))

    return render_template('admin/book_form.html', form=form, title='Add New Book')


@admin_bp.route('/books/edit/<int:book_id>', methods=['GET', 'POST'])
def edit_book(book_id):
    """Update existing book details."""
    book = db.session.get(Book, book_id)
    if not book:
        flash('Book not found.', 'danger')
        return redirect(url_for('admin.books'))

    form = BookForm(obj=book)
    if form.validate_on_submit():
        # Check ISBN uniqueness if changed
        new_isbn = form.isbn.data.strip()
        if new_isbn != book.isbn:
            conflict = Book.query.filter_by(isbn=new_isbn).first()
            if conflict:
                flash(f'ISBN {new_isbn} is already assigned to "{conflict.title}".', 'danger')
                return render_template('admin/book_form.html', form=form, title='Edit Book', book=book)

        # Calculate difference in total copies to update available copies safely
        issued_count = book.total_copies - book.available_copies
        new_total = form.total_copies.data

        if new_total < issued_count:
            flash(
                f'Cannot reduce total copies to {new_total}. Currently {issued_count} copies are issued to students.',
                'warning'
            )
            return render_template('admin/book_form.html', form=form, title='Edit Book', book=book)

        book.title = sanitize_input(form.title.data.strip())
        book.author = sanitize_input(form.author.data.strip())
        book.isbn = new_isbn
        book.category = form.category.data
        book.total_copies = new_total
        book.available_copies = new_total - issued_count
        book.shelf_location = sanitize_input(form.shelf_location.data.strip()) if form.shelf_location.data else 'General'
        book.description = sanitize_input(form.description.data.strip()) if form.description.data else ''

        db.session.commit()
        log_activity(action='BOOK_UPDATED', details=f"Updated details for book ID {book.id}: '{book.title}'.")
        flash(f'Book "{book.title}" updated successfully!', 'success')
        return redirect(url_for('admin.books'))

    return render_template('admin/book_form.html', form=form, title='Edit Book', book=book)


@admin_bp.route('/books/delete/<int:book_id>', methods=['POST'])
def delete_book(book_id):
    """Delete a book from the catalog if no active issues or requests exist."""
    book = db.session.get(Book, book_id)
    if not book:
        flash('Book not found.', 'danger')
        return redirect(url_for('admin.books'))

    active_issues = IssueRecord.query.filter(
        IssueRecord.book_id == book.id,
        IssueRecord.status.in_(['issued', 'pending'])
    ).count()

    if active_issues > 0:
        flash(f'Cannot delete "{book.title}". There are {active_issues} active loan(s) or request(s).', 'danger')
        return redirect(url_for('admin.books'))

    title = book.title
    db.session.delete(book)
    db.session.commit()

    log_activity(action='BOOK_DELETED', details=f"Deleted book '{title}' (ID: {book_id}).")
    flash(f'Book "{title}" has been deleted from catalog.', 'info')
    return redirect(url_for('admin.books'))


# ---------------------------------------------------------
# Student Account Management
# ---------------------------------------------------------

@admin_bp.route('/students')
def students():
    """List all registered students with loan counts and account security status."""
    student_list = User.query.filter_by(role='student').order_by(User.full_name.asc()).all()

    # Precompute summary counts for each student
    student_data = []
    for s in student_list:
        active_loans = IssueRecord.query.filter_by(user_id=s.id, status='issued').count()
        unpaid_fines = db.session.query(
            func.coalesce(func.sum(Fine.amount), 0.0)
        ).filter_by(user_id=s.id, status='unpaid').scalar()

        student_data.append({
            'user': s,
            'active_loans': active_loans,
            'unpaid_fines': round(unpaid_fines, 2),
            'is_locked': s.is_locked()
        })

    return render_template('admin/students.html', students=student_data)


@admin_bp.route('/students/<int:student_id>/toggle-status', methods=['POST'])
def toggle_student_status(student_id):
    """Activate or deactivate a student account."""
    student = db.session.get(User, student_id)
    if not student or student.role != 'student':
        flash('Student account not found.', 'danger')
        return redirect(url_for('admin.students'))

    student.is_active = not student.is_active
    db.session.commit()

    status_str = 'activated' if student.is_active else 'deactivated'
    log_activity(
        action='STUDENT_STATUS_TOGGLED',
        details=f"Admin {status_str} student account {student.username} (Roll: {student.roll_number})."
    )
    flash(f"Student account {student.username} has been {status_str}.", 'success')
    return redirect(url_for('admin.students'))


@admin_bp.route('/students/<int:student_id>/unlock', methods=['POST'])
def unlock_student(student_id):
    """Unlock a student account that was locked due to brute-force attempts."""
    student = db.session.get(User, student_id)
    if not student or student.role != 'student':
        flash('Student not found.', 'danger')
        return redirect(url_for('admin.students'))

    student.reset_failed_logins()
    log_activity(
        action='STUDENT_ACCOUNT_UNLOCKED',
        details=f"Admin manually unlocked student account {student.username}."
    )
    flash(f"Student account {student.username} has been unlocked successfully.", 'success')
    return redirect(url_for('admin.students'))


# ---------------------------------------------------------
# Issue & Return Workflow
# ---------------------------------------------------------

@admin_bp.route('/issue-return', methods=['GET'])
def issue_return():
    """Central view for managing book requests, direct issues, and returns."""
    sync_overdue_fines()

    direct_form = DirectIssueForm()
    # Populate dynamic choices
    direct_form.student_id.choices = [
        (s.id, f"{s.roll_number} - {s.full_name} ({s.username})")
        for s in User.query.filter_by(role='student', is_active=True).order_by(User.roll_number.asc()).all()
    ]
    direct_form.book_id.choices = [
        (b.id, f"{b.title} [Available: {b.available_copies}]")
        for b in Book.query.filter(Book.available_copies > 0).order_by(Book.title.asc()).all()
    ]

    # Pending student requests
    pending_requests = IssueRecord.query.filter_by(status='pending').order_by(IssueRecord.created_at.asc()).all()

    # Active issued books
    active_issues = IssueRecord.query.filter_by(status='issued').order_by(IssueRecord.due_date.asc()).all()

    return render_template(
        'admin/issue_return.html',
        direct_form=direct_form,
        pending_requests=pending_requests,
        active_issues=active_issues,
        today=date.today()
    )


@admin_bp.route('/issue/direct', methods=['POST'])
def direct_issue():
    """Admin directly issues a book to a selected student."""
    direct_form = DirectIssueForm()
    direct_form.student_id.choices = [
        (s.id, s.username) for s in User.query.filter_by(role='student').all()
    ]
    direct_form.book_id.choices = [
        (b.id, b.title) for b in Book.query.all()
    ]

    if direct_form.validate_on_submit():
        student = db.session.get(User, direct_form.student_id.data)
        book = db.session.get(Book, direct_form.book_id.data)

        if not student or not student.is_active:
            flash('Selected student is inactive or does not exist.', 'danger')
            return redirect(url_for('admin.issue_return'))

        if not book or book.available_copies <= 0:
            flash(f'Cannot issue book. No copies of "{book.title if book else "Unknown"}" are available.', 'danger')
            return redirect(url_for('admin.issue_return'))

        # Check borrow limits
        max_borrow = current_app.config.get('MAX_BORROW_LIMIT', 3)
        current_borrow_count = IssueRecord.query.filter_by(user_id=student.id, status='issued').count()
        if current_borrow_count >= max_borrow:
            flash(
                f'Student {student.roll_number} already has {current_borrow_count} active loans '
                f'(Max limit is {max_borrow}).',
                'warning'
            )
            return redirect(url_for('admin.issue_return'))

        # Perform issue
        borrow_days = direct_form.due_days.data or 14
        today = date.today()
        due = today + timedelta(days=borrow_days)

        issue_record = IssueRecord(
            user_id=student.id,
            book_id=book.id,
            issue_date=today,
            due_date=due,
            status='issued',
            issued_by_id=current_user.id,
            notes=sanitize_input(direct_form.notes.data.strip()) if direct_form.notes.data else None
        )

        book.available_copies -= 1
        db.session.add(issue_record)
        db.session.commit()

        log_activity(
            action='BOOK_ISSUED_DIRECT',
            details=f"Admin issued '{book.title}' to {student.username} (Due: {due})."
        )
        flash(f'Successfully issued "{book.title}" to student {student.full_name}. Due Date: {due}', 'success')
    else:
        flash('Failed to issue book. Please check form inputs.', 'danger')

    return redirect(url_for('admin.issue_return'))


@admin_bp.route('/issue/<int:record_id>/approve', methods=['POST'])
def approve_request(record_id):
    """Approve a student's pending book request."""
    record = db.session.get(IssueRecord, record_id)
    if not record or record.status != 'pending':
        flash('Invalid or non-pending request.', 'danger')
        return redirect(url_for('admin.issue_return'))

    book = record.book
    if book.available_copies <= 0:
        flash(f'Cannot approve request: No copies of "{book.title}" currently available.', 'warning')
        return redirect(url_for('admin.issue_return'))

    borrow_days = current_app.config.get('BORROW_DURATION_DAYS', 14)
    today = date.today()
    due = today + timedelta(days=borrow_days)

    record.issue_date = today
    record.due_date = due
    record.status = 'issued'
    record.issued_by_id = current_user.id
    book.available_copies -= 1

    db.session.commit()

    log_activity(
        action='REQUEST_APPROVED',
        details=f"Approved request #{record.id}: '{book.title}' issued to {record.student.username} (Due: {due})."
    )
    flash(f'Request approved! "{book.title}" issued to {record.student.full_name}. Due Date: {due}', 'success')
    return redirect(url_for('admin.issue_return'))


@admin_bp.route('/issue/<int:record_id>/reject', methods=['POST'])
def reject_request(record_id):
    """Reject a student's pending book request."""
    record = db.session.get(IssueRecord, record_id)
    if not record or record.status != 'pending':
        flash('Invalid request record.', 'danger')
        return redirect(url_for('admin.issue_return'))

    record.status = 'rejected'
    db.session.commit()

    log_activity(
        action='REQUEST_REJECTED',
        details=f"Rejected request #{record.id} for book '{record.book.title}' from {record.student.username}."
    )
    flash(f'Book request for "{record.book.title}" rejected.', 'info')
    return redirect(url_for('admin.issue_return'))


@admin_bp.route('/issue/<int:record_id>/return', methods=['POST'])
def process_return(record_id):
    """Process the return of an issued book and record any overdue fines."""
    record = db.session.get(IssueRecord, record_id)
    if not record or record.status != 'issued':
        flash('Invalid issue record for return.', 'danger')
        return redirect(url_for('admin.issue_return'))

    today = date.today()
    record.return_date = today
    record.status = 'returned'

    # Return physical copy to inventory
    book = record.book
    book.available_copies += 1

    # Overdue fine calculation
    daily_rate = current_app.config.get('DAILY_FINE_RATE', 5.0)
    fine_msg = ""
    if record.due_date and today > record.due_date:
        overdue_days = (today - record.due_date).days
        fine_amount = round(overdue_days * daily_rate, 2)

        # Record fine in database
        fine = Fine.query.filter_by(issue_record_id=record.id).first()
        if not fine:
            fine = Fine(
                issue_record_id=record.id,
                user_id=record.user_id,
                amount=fine_amount,
                status='unpaid'
            )
            db.session.add(fine)
        else:
            fine.amount = fine_amount

        fine_msg = f" Book was overdue by {overdue_days} day(s). Late fine of ₹{fine_amount} recorded."

    db.session.commit()

    log_activity(
        action='BOOK_RETURNED',
        details=f"Book '{book.title}' returned by {record.student.username}.{fine_msg}"
    )
    flash(f'Book "{book.title}" returned successfully!{fine_msg}', 'success')
    return redirect(url_for('admin.issue_return'))


# ---------------------------------------------------------
# Fine Management
# ---------------------------------------------------------

@admin_bp.route('/fines')
def fines():
    """List all calculated fines, status, and manual synchronization."""
    sync_overdue_fines()

    status_filter = request.args.get('status', '').strip()
    query = Fine.query.join(User).join(IssueRecord)

    if status_filter in ['unpaid', 'paid']:
        query = query.filter(Fine.status == status_filter)

    fine_records = query.order_by(Fine.created_at.desc()).all()

    total_unpaid = db.session.query(
        func.coalesce(func.sum(Fine.amount), 0.0)
    ).filter_by(status='unpaid').scalar()

    total_paid = db.session.query(
        func.coalesce(func.sum(Fine.amount), 0.0)
    ).filter_by(status='paid').scalar()

    return render_template(
        'admin/fines.html',
        fines=fine_records,
        status_filter=status_filter,
        total_unpaid=round(total_unpaid, 2),
        total_paid=round(total_paid, 2)
    )


@admin_bp.route('/fines/<int:fine_id>/pay', methods=['POST'])
def mark_fine_paid(fine_id):
    """Mark an unpaid fine as settled."""
    fine = db.session.get(Fine, fine_id)
    if not fine or fine.status == 'paid':
        flash('Fine already paid or not found.', 'info')
        return redirect(url_for('admin.fines'))

    fine.status = 'paid'
    fine.paid_date = datetime.now(timezone.utc)
    db.session.commit()

    log_activity(
        action='FINE_COLLECTED',
        details=f"Admin collected fine of ₹{fine.amount} from {fine.user.username} (Fine ID: {fine.id})."
    )
    flash(f'Fine of ₹{fine.amount} for student {fine.user.full_name} marked as PAID.', 'success')
    return redirect(url_for('admin.fines'))


# ---------------------------------------------------------
# Security Audit Logs
# ---------------------------------------------------------

@admin_bp.route('/activity-logs')
def activity_logs():
    """Display comprehensive security and administrative audit trail."""
    action_filter = request.args.get('action', '').strip()
    user_search = request.args.get('user', '').strip()

    query = ActivityLog.query
    if action_filter:
        query = query.filter(ActivityLog.action.ilike(f"%{action_filter}%"))
    if user_search:
        query = query.filter(ActivityLog.username.ilike(f"%{user_search}%"))

    logs = query.order_by(ActivityLog.timestamp.desc()).limit(150).all()
    actions = [r[0] for r in db.session.query(ActivityLog.action).distinct().all()]

    return render_template(
        'admin/activity_logs.html',
        logs=logs,
        actions=actions,
        selected_action=action_filter,
        user_search=user_search
    )
