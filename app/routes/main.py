"""
Granthify - Main & Public Routes
Landing page, public catalog search, and error dispatchers.
"""

from flask import Blueprint, render_template, redirect, url_for, request
from flask_login import current_user
from app.models import Book, User, IssueRecord
from app.forms import BookSearchForm

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    """Home landing page. Authenticated users are redirected to their respective dashboards."""
    if current_user.is_authenticated:
        if current_user.role == 'admin':
            return redirect(url_for('admin.dashboard'))
        return redirect(url_for('student.dashboard'))

    # Display public statistics and showcase books
    total_books = Book.query.count()
    total_students = User.query.filter_by(role='student').count()
    featured_books = Book.query.order_by(Book.id.desc()).limit(6).all()

    return render_template(
        'index.html',
        total_books=total_books,
        total_students=total_students,
        featured_books=featured_books
    )


@main_bp.route('/catalog')
def public_catalog():
    """Publicly searchable catalog view for unregistered visitors or preview."""
    form = BookSearchForm(request.args)
    query = Book.query

    keyword = request.args.get('keyword', '').strip()
    category = request.args.get('category', '').strip()
    availability = request.args.get('availability', '').strip()

    if keyword:
        # Prevent SQL injection by utilizing SQLAlchemy parameterized LIKE expressions
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
    categories = [c[0] for c in form.category.choices if c[0]]

    return render_template(
        'student/catalog.html',
        books=books,
        form=form,
        is_public=not current_user.is_authenticated,
        categories=categories
    )
