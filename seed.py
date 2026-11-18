"""
Granthify - Database Seeding Script
Initializes SQLite schema, generates hashed administrator and student accounts,
and populates academic textbooks across computer science and cybersecurity disciplines.
"""

import os
from datetime import date, timedelta
from app import create_app, db
from app.models import User, Book, IssueRecord, Fine, ActivityLog


def seed_database(target_app=None):
    """Seed baseline catalog and default accounts."""
    app_instance = target_app or create_app(os.getenv('FLASK_ENV', 'development'))
    with app_instance.app_context():
        print("[+] Initializing database schema...")
        db.create_all()

        # 1. Seed Administrator Account
        admin_user = User.query.filter_by(username='admin').first()
        if not admin_user:
            admin_user = User(
                username='admin',
                email='admin@granthify.edu',
                full_name='Security Administrator',
                role='admin',
                is_active=True
            )
            admin_user.set_password('AdminPassword123!')
            db.session.add(admin_user)
            print("[+] Created Default Admin Account: 'admin' / 'AdminPassword123!'")
        else:
            print("[*] Admin account already exists.")

        # 2. Seed Demo Student Account
        student_user = User.query.filter_by(username='cyber_student').first()
        if not student_user:
            student_user = User(
                username='cyber_student',
                email='student@granthify.edu',
                full_name='Harsh Kumar',
                roll_number='23CYBER042',
                phone='+91 9876543210',
                role='student',
                is_active=True
            )
            student_user.set_password('StudentPass123!')
            db.session.add(student_user)
            print("[+] Created Demo Student Account: 'cyber_student' / 'StudentPass123!'")
        else:
            print("[*] Demo student account already exists.")

        # Second Demo Student
        student_user2 = User.query.filter_by(username='rahul_sharma').first()
        if not student_user2:
            student_user2 = User(
                username='rahul_sharma',
                email='rahul@granthify.edu',
                full_name='Rahul Sharma',
                roll_number='23CYBER018',
                phone='+91 9123456780',
                role='student',
                is_active=True
            )
            student_user2.set_password('StudentPass123!')
            db.session.add(student_user2)

        db.session.commit()

        # 3. Seed Standard Academic Books
        books_data = [
            {
                "title": "Applied Cryptography: Protocols, Algorithms, and Source Code in C",
                "author": "Bruce Schneier",
                "isbn": "978-1119096726",
                "category": "Cyber Security",
                "total_copies": 4,
                "available_copies": 4,
                "shelf_location": "SEC-R1-S1",
                "description": "Definitive work on modern cryptography covering symmetric ciphers, public key algorithms, cryptographic protocols, and implementation caveats."
            },
            {
                "title": "The Web Application Hacker's Handbook: Finding and Exploiting Security Flaws",
                "author": "Dafydd Stuttard, Marcus Pinto",
                "isbn": "978-1118026472",
                "category": "Cyber Security",
                "total_copies": 3,
                "available_copies": 3,
                "shelf_location": "SEC-R1-S2",
                "description": "Comprehensive guide to dissecting, assessing, and remediating vulnerabilities in web applications, including SQL injection, XSS, and authentication bypasses."
            },
            {
                "title": "Practical Malware Analysis: The Hands-On Guide to Dissecting Malicious Software",
                "author": "Michael Sikorski, Andrew Honig",
                "isbn": "978-1593272906",
                "category": "Cyber Security",
                "total_copies": 3,
                "available_copies": 3,
                "shelf_location": "SEC-R2-S1",
                "description": "Step-by-step introduction to static and dynamic malware reverse engineering using disassemblers, debuggers, and behavioral sandboxes."
            },
            {
                "title": "CompTIA Security+ All-in-One Exam Guide (SY0-701)",
                "author": "Wm. Arthur Conklin, Gregory White",
                "isbn": "978-1265042455",
                "category": "Cyber Security",
                "total_copies": 5,
                "available_copies": 5,
                "shelf_location": "SEC-R2-S2",
                "description": "Core foundation covering cybersecurity fundamentals, network security controls, threat vectors, risk management, and identity management."
            },
            {
                "title": "Operating System Concepts (10th Edition)",
                "author": "Abraham Silberschatz, Peter B. Galvin, Greg Gagne",
                "isbn": "978-1119800361",
                "category": "Computer Science",
                "total_copies": 6,
                "available_copies": 6,
                "shelf_location": "CS-R1-S1",
                "description": "Foundational operating systems textbook covering kernel architecture, process concurrency, virtual memory management, file systems, and system security."
            },
            {
                "title": "Introduction to Algorithms (CLRS 4th Edition)",
                "author": "Thomas H. Cormen, Charles E. Leiserson, Ronald L. Rivest, Clifford Stein",
                "isbn": "978-0262046305",
                "category": "Computer Science",
                "total_copies": 5,
                "available_copies": 5,
                "shelf_location": "CS-R1-S2",
                "description": "Authoritative guide to data structures, graph theory algorithms, dynamic programming, NP-completeness, and algorithmic computational complexity."
            },
            {
                "title": "Computer Networking: A Top-Down Approach (8th Edition)",
                "author": "James F. Kurose, Keith W. Ross",
                "isbn": "978-0136681557",
                "category": "Networking",
                "total_copies": 4,
                "available_copies": 4,
                "shelf_location": "NET-R1-S1",
                "description": "Top-down tour of computer communications spanning application layer protocols (HTTP/DNS), transport layer (TCP/UDP), network routing, and link layer."
            },
            {
                "title": "Artificial Intelligence: A Modern Approach (4th Edition)",
                "author": "Stuart Russell, Peter Norvig",
                "isbn": "978-0134610993",
                "category": "Artificial Intelligence",
                "total_copies": 3,
                "available_copies": 3,
                "shelf_location": "AI-R1-S1",
                "description": "Leading textbook exploring intelligent agent architectures, search algorithms, probabilistic reasoning, machine learning, and deep neural models."
            },
            {
                "title": "Clean Code: A Handbook of Agile Software Craftsmanship",
                "author": "Robert C. Martin",
                "isbn": "978-0132350884",
                "category": "Software Engineering",
                "total_copies": 4,
                "available_copies": 4,
                "shelf_location": "SE-R1-S1",
                "description": "Essential software design paradigms covering clean syntax, SOLID principles, meaningful naming conventions, test-driven development, and refactoring."
            },
            {
                "title": "Database System Concepts (7th Edition)",
                "author": "Abraham Silberschatz, Henry F. Korth, S. Sudarshan",
                "isbn": "978-0078022159",
                "category": "Computer Science",
                "total_copies": 4,
                "available_copies": 4,
                "shelf_location": "CS-R2-S1",
                "description": "Theoretical and practical foundations of relational databases, SQL queries, transaction atomicity, indexing architectures, and query optimization."
            }
        ]

        for b_data in books_data:
            existing_book = Book.query.filter_by(isbn=b_data["isbn"]).first()
            if not existing_book:
                book = Book(**b_data)
                db.session.add(book)

        db.session.commit()
        print(f"[+] Populated {len(books_data)} standard academic textbooks.")

        # 4. Create sample initial loan and request for demo experience
        book1 = Book.query.filter_by(isbn="978-1119096726").first()
        book2 = Book.query.filter_by(isbn="978-0262046305").first()

        # Active Loan (issued 5 days ago, due in 9 days)
        if book1 and not IssueRecord.query.filter_by(user_id=student_user.id, book_id=book1.id).first():
            today = date.today()
            loan = IssueRecord(
                user_id=student_user.id,
                book_id=book1.id,
                issue_date=today - timedelta(days=5),
                due_date=today + timedelta(days=9),
                status='issued',
                issued_by_id=admin_user.id
            )
            book1.available_copies -= 1
            db.session.add(loan)

        # Pending Request
        if book2 and not IssueRecord.query.filter_by(user_id=student_user.id, book_id=book2.id).first():
            req = IssueRecord(
                user_id=student_user.id,
                book_id=book2.id,
                status='pending'
            )
            db.session.add(req)

        # 5. Initial Security Audit Log
        if ActivityLog.query.count() == 0:
            log1 = ActivityLog(
                user_id=admin_user.id,
                username=admin_user.username,
                action='SYSTEM_INITIALIZED',
                ip_address='127.0.0.1',
                details='Database schema generated and baseline catalog initialized.'
            )
            db.session.add(log1)

        db.session.commit()
        print("[+] Sample loan and reservation requests initialized successfully.")
        print("\n" + "=" * 60)
        print("GRANTHIFY SYSTEM INITIALIZATION COMPLETE")
        print("=" * 60)
        print("Administrator Credentials:")
        print("  Username : admin")
        print("  Password : AdminPassword123!")
        print("  Role     : Administrator (Full Access)")
        print("-" * 60)
        print("Demo Student Credentials:")
        print("  Username : cyber_student")
        print("  Password : StudentPass123!")
        print("  Roll No  : 23CYBER042")
        print("  Role     : Student")
        print("=" * 60 + "\n")

if __name__ == '__main__':
    seed_database()
