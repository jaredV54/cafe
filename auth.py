from functools import wraps
from flask import redirect, url_for, session
import sqlite3

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated

def is_admin():
    return session.get("role") == "admin"

def init_db(db_path):
    with sqlite3.connect(db_path) as conn:
        cur = conn.cursor()

        # Users table
        cur.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                passkey TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('admin', 'staff')),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
        ''')

        # Products table
        cur.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                price DECIMAL(10, 2) NOT NULL,
                is_available BOOLEAN DEFAULT 1,
                category TEXT NOT NULL
            );
        ''')

        # Transactions table
        cur.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                transaction_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                total_amount DECIMAL(10, 2) NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );
        ''')

        # Transaction Details table
        cur.execute('''
            CREATE TABLE IF NOT EXISTS transaction_details (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                transaction_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                product_name TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                price_each DECIMAL(10, 2) NOT NULL,
                subtotal DECIMAL(10, 2) NOT NULL,
                FOREIGN KEY (transaction_id) REFERENCES transactions(id),
                FOREIGN KEY (product_id) REFERENCES products(id)
            );
        ''')

        # Create default admin user if no users exist
        cur.execute("SELECT COUNT(*) FROM users")
        if cur.fetchone()[0] == 0:
            cur.execute("INSERT INTO users (username, passkey, role) VALUES (?, ?, ?)",
                        ("admin", "admin", "admin"))

        conn.commit()
