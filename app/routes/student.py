"""
Granthify - Student Blueprint
Student portal: personal dashboard, catalog search & filtering, book requests,
active loans tracking, borrowing history, and fine status.
"""

from datetime import date
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from sqlalchemy import func
from app import db
from app.models import Book, IssueRecord, Fine
from app.forms import BookSearchForm
from app.decorators import student_required
from app.utils import log_activity, sync_overdue_fines

student_bp = Blueprint('student', __name__)


@student_bp.before_request
@login_required
@student_required
def enforce_student_security():
    """Verify that current user is an authenticated active student."""
    pass


@student_bp.route('/dashboard')
def dashboard():
    """Student dashboard overview with active loans, alerts, and due date trackers."""
    # Ensure any accrued overdue fines are synced
    sync_overdue_fines()

    today = date.today()

    # Active loans
    active_loans = IssueRecord.query.filter_by(
        user_id=current_user.id,
        status='issued'
    ).order_by(IssueRecord.due_date.asc()).all()

    # Pending requests
    pending_requests = IssueRecord.query.filter_by(
        user_id=current_user.id,
        status='pending'
    ).order_by(IssueRecord.created_at.desc()).all()

    # Total unpaid fines
    unpaid_fines_total = db.session.query(
        func.coalesce(func.sum(Fine.amount), 0.0)
    ).filter_by(user_id=current_user.id, status='unpaid').scalar()

    # Books due soon (within 3 days) or already overdue
    due_soon_count = sum(1 for loan in active_loans if loan.due_date and 0 <= (loan.due_date - today).days <= 3)
    overdue_count = sum(1 for loan in active_loans if loan.is_overdue)

    # Recently added books to explore
    recent_books = Book.query.order_by(Book.id.desc()).limit(4).all()

    return render_template(
        'student/dashboard.html',
        active_loans=active_loans,
        pending_requests=pending_requests,
        unpaid_fines_total=round(unpaid_fines_total, 2),
        due_soon_count=due_soon_count,
        overdue_count=overdue_count,
        recent_books=recent_books,
        today=today
    )


@student_bp.route('/catalog')
def catalog():
    """Browse library catalog with category filters and title/author/ISBN search."""
    form = BookSearchForm(request.args)
    query = Book.query

    keyword = request.args.get('keyword', '').strip()
    category = request.args.get('category', '').strip()
    availability = request.args.get('availability', '').strip()

    if keyword:
        # SQL Injection prevention via SQLAlchemy parameterized like expression
        search_pattern = f"%{keyword}%"
        query = query.filter(
            (Book.title.ilike(search_pattern)) |
            (Book.author.ilike(search_pattern)) |
            (Book.isbn.ilike(search_pattern))
        )

    if category:
        query = query.filter(Book.category == category)

    if availability == 'available':
        query = query.filter(Book.available_copies > 0)
    elif availability == 'out_of_stock':
        query = query.filter(Book.available_copies <= 0)

    books = query.order_by(Book.title.asc()).all()

    # Preload student's currently active or requested book IDs to disable duplicate request button
    active_book_ids = {
        r.book_id for r in IssueRecord.query.filter(
            IssueRecord.user_id == current_user.id,
            IssueRecord.status.in_(['pending', 'issued'])
        ).all()
    }

    return render_template(
        'student/catalog.html',
        books=books,
        form=form,
        active_book_ids=active_book_ids,
        is_public=False
    )


@student_bp.route('/request-book/<int:book_id>', methods=['POST'])
def request_book(book_id):
    """Submit a borrowing request for a book in catalog."""
    book = db.session.get(Book, book_id)
    if not book:
        flash('Requested book does not exist.', 'danger')
        return redirect(url_for('student.catalog'))

    # Check copy availability
    if book.available_copies <= 0:
        flash(f'Sorry, all copies of "{book.title}" are currently issued.', 'warning')
        return redirect(url_for('student.catalog'))

    # Check for duplicate active loan or pending request
    existing_record = IssueRecord.query.filter(
        IssueRecord.user_id == current_user.id,
        IssueRecord.book_id == book.id,
        IssueRecord.status.in_(['pending', 'issued'])
    ).first()

    if existing_record:
        if existing_record.status == 'pending':
            flash(f'You already have a pending request for "{book.title}".', 'info')
        else:
            flash(f'You currently have a copy of "{book.title}" issued.', 'info')
        return redirect(url_for('student.catalog'))

    # Check borrow limit
    max_borrow = current_app.config.get('MAX_BORROW_LIMIT', 3)
    active_loans_count = IssueRecord.query.filter_by(user_id=current_user.id, status='issued').count()
    pending_count = IssueRecord.query.filter_by(user_id=current_user.id, status='pending').count()

    if (active_loans_count + pending_count) >= max_borrow:
        flash(
            f'You have reached the maximum allowed limit of {max_borrow} active books / requests.',
            'warning'
        )
        return redirect(url_for('student.catalog'))

    # Check for high outstanding unpaid fines
    unpaid_fines = db.session.query(
        func.coalesce(func.sum(Fine.amount), 0.0)
    ).filter_by(user_id=current_user.id, status='unpaid').scalar()

    if unpaid_fines > 100.0:
        flash(
            f'You have outstanding unpaid fines of ₹{round(unpaid_fines, 2)}. '
            f'Please clear pending fines at the library counter before borrowing new books.',
            'danger'
        )
        return redirect(url_for('student.my_fines'))

    # Create request
    new_request = IssueRecord(
        user_id=current_user.id,
        book_id=book.id,
        status='pending'
    )
    db.session.add(new_request)
    db.session.commit()

    log_activity(
        action='BOOK_REQUESTED',
        details=f"Student requested book '{book.title}' (ISBN: {book.isbn})."
    )
    flash(f'Request submitted for "{book.title}". The librarian will review and approve your request.', 'success')
    return redirect(url_for('student.my_books'))


@student_bp.route('/my-books')
def my_books():
    """Display student's active issued books and pending book requests."""
    sync_overdue_fines()

    active_loans = IssueRecord.query.filter_by(
        user_id=current_user.id,
        status='issued'
    ).order_by(IssueRecord.due_date.asc()).all()

    pending_requests = IssueRecord.query.filter_by(
        user_id=current_user.id,
        status='pending'
    ).order_by(IssueRecord.created_at.desc()).all()

    return render_template(
        'student/my_books.html',
        active_loans=active_loans,
        pending_requests=pending_requests,
        today=date.today()
    )


@student_bp.route('/history')
def history():
    """Display past borrowing history (returned books and rejected requests)."""
    past_records = IssueRecord.query.filter(
        IssueRecord.user_id == current_user.id,
        IssueRecord.status.in_(['returned', 'rejected'])
    ).order_by(IssueRecord.id.desc()).all()

    return render_template('student/history.html', past_records=past_records)


@student_bp.route('/fines')
def my_fines():
    """Display student's fine breakdown, overdue penalties, and payment status."""
    sync_overdue_fines()

    fine_records = Fine.query.filter_by(user_id=current_user.id).order_by(Fine.created_at.desc()).all()

    total_unpaid = sum(f.amount for f in fine_records if f.status == 'unpaid')
    total_paid = sum(f.amount for f in fine_records if f.status == 'paid')

    return render_template(
        'student/my_fines.html',
        fine_records=fine_records,
        total_unpaid=round(total_unpaid, 2),
        total_paid=round(total_paid, 2)
    )
