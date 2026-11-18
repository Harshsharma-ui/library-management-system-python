"""
Granthify - WTForms Validation Forms
Provides strict input validation, length constraints, regex matching, and CSRF integration.
"""

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, IntegerField, TextAreaField, SelectField
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError, Regexp, Optional, NumberRange
from app.models import User, Book


class LoginForm(FlaskForm):
    """User authentication form."""
    username = StringField('Username or Email', validators=[
        DataRequired(message='Username is required.'),
        Length(min=3, max=120, message='Username or email must be between 3 and 120 characters.')
    ])
    password = PasswordField('Password', validators=[
        DataRequired(message='Password is required.')
    ])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')


class StudentRegistrationForm(FlaskForm):
    """Student registration form with validation against duplicate credentials."""
    username = StringField('Username', validators=[
        DataRequired(message='Username is required.'),
        Length(min=3, max=50, message='Username must be between 3 and 50 characters.'),
        Regexp(r'^[a-zA-Z0-9_.]+$', message='Username may only contain letters, numbers, dots, and underscores.')
    ])
    email = StringField('Email Address', validators=[
        DataRequired(message='Email address is required.'),
        Email(message='Please provide a valid email address.'),
        Length(max=120)
    ])
    full_name = StringField('Full Name', validators=[
        DataRequired(message='Full name is required.'),
        Length(min=2, max=100)
    ])
    roll_number = StringField('College Roll Number', validators=[
        DataRequired(message='College roll number is required.'),
        Length(min=3, max=30),
        Regexp(r'^[a-zA-Z0-9\-_]+$', message='Roll number contains invalid characters.')
    ])
    phone = StringField('Phone Number', validators=[
        Optional(),
        Length(min=10, max=15, message='Phone number should be between 10 and 15 digits.'),
        Regexp(r'^\+?[0-9\- ]+$', message='Phone number must contain only numbers and optional + or -.')
    ])
    password = PasswordField('Password', validators=[
        DataRequired(message='Password is required.'),
        Length(min=8, message='Password must be at least 8 characters long.'),
        Regexp(
            r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)',
            message='Password must include at least one uppercase letter, one lowercase letter, and one number.'
        )
    ])
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(message='Please confirm your password.'),
        EqualTo('password', message='Passwords must match.')
    ])
    submit = SubmitField('Create Account')

    def validate_username(self, field):
        user = User.query.filter_by(username=field.data.strip()).first()
        if user:
            raise ValidationError('This username is already taken. Please choose another.')

    def validate_email(self, field):
        user = User.query.filter_by(email=field.data.strip().lower()).first()
        if user:
            raise ValidationError('An account with this email address already exists.')

    def validate_roll_number(self, field):
        user = User.query.filter_by(roll_number=field.data.strip().upper()).first()
        if user:
            raise ValidationError('A student with this roll number is already registered.')


class BookForm(FlaskForm):
    """Admin form for adding and editing book records."""
    title = StringField('Book Title', validators=[
        DataRequired(message='Book title is required.'),
        Length(min=1, max=200)
    ])
    author = StringField('Author', validators=[
        DataRequired(message='Author name is required.'),
        Length(min=1, max=150)
    ])
    isbn = StringField('ISBN Number', validators=[
        DataRequired(message='ISBN is required.'),
        Length(min=10, max=20, message='ISBN must be between 10 and 20 characters.'),
        Regexp(r'^[0-9\-X]+$', message='ISBN must contain valid characters (numbers, dashes, or X).')
    ])
    category = SelectField('Category', choices=[
        ('Computer Science', 'Computer Science & IT'),
        ('Cyber Security', 'Cyber Security & Cryptography'),
        ('Artificial Intelligence', 'Artificial Intelligence & Data Science'),
        ('Software Engineering', 'Software Engineering'),
        ('Networking', 'Networking & Cloud Computing'),
        ('Mathematics', 'Mathematics & Discrete Structures'),
        ('Electronics', 'Electronics & Hardware'),
        ('General', 'General Reading & Literature')
    ], validators=[DataRequired()])
    total_copies = IntegerField('Total Copies', validators=[
        DataRequired(message='Number of copies is required.'),
        NumberRange(min=1, max=500, message='Total copies must be between 1 and 500.')
    ])
    shelf_location = StringField('Shelf / Rack Location', validators=[
        Optional(),
        Length(max=50)
    ])
    description = TextAreaField('Book Description / Synopsis', validators=[
        Optional(),
        Length(max=1000)
    ])
    submit = SubmitField('Save Book')


class DirectIssueForm(FlaskForm):
    """Admin form to issue a book directly to a student."""
    student_id = SelectField('Select Student', coerce=int, validators=[DataRequired()])
    book_id = SelectField('Select Book', coerce=int, validators=[DataRequired()])
    due_days = IntegerField('Borrow Period (Days)', default=14, validators=[
        DataRequired(),
        NumberRange(min=1, max=90, message='Borrow period must be between 1 and 90 days.')
    ])
    notes = StringField('Notes (Optional)', validators=[Optional(), Length(max=255)])
    submit = SubmitField('Issue Book')


class BookSearchForm(FlaskForm):
    """Filter and search form for the book catalog."""
    keyword = StringField('Search by Title, Author, or ISBN', validators=[Optional(), Length(max=100)])
    category = SelectField('Category', choices=[
        ('', 'All Categories'),
        ('Computer Science', 'Computer Science & IT'),
        ('Cyber Security', 'Cyber Security & Cryptography'),
        ('Artificial Intelligence', 'Artificial Intelligence & Data Science'),
        ('Software Engineering', 'Software Engineering'),
        ('Networking', 'Networking & Cloud Computing'),
        ('Mathematics', 'Mathematics & Discrete Structures'),
        ('Electronics', 'Electronics & Hardware'),
        ('General', 'General')
    ], validators=[Optional()])
    availability = SelectField('Availability', choices=[
        ('', 'All Books'),
        ('available', 'Only Available in Stock'),
        ('out_of_stock', 'Out of Stock')
    ], validators=[Optional()])
    submit = SubmitField('Search')


class ChangePasswordForm(FlaskForm):
    """Form to allow users to update their password securely."""
    current_password = PasswordField('Current Password', validators=[DataRequired()])
    new_password = PasswordField('New Password', validators=[
        DataRequired(),
        Length(min=8, message='Password must be at least 8 characters long.'),
        Regexp(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)',
               message='Password must include an uppercase letter, lowercase letter, and a digit.')
    ])
    confirm_password = PasswordField('Confirm New Password', validators=[
        DataRequired(),
        EqualTo('new_password', message='Passwords must match.')
    ])
    submit = SubmitField('Update Password')
