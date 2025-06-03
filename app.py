from flask import Flask, render_template, redirect, url_for, session, request, flash
from auth import login_required, is_admin, init_db
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import json
import re
from dotenv import load_dotenv
import os

load_dotenv()  

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'secret')  

DB = os.getenv('DATABASE_URL', 'database.db')
# When deployed
# DB = os.getenv('DATABASE_URL', os.path.join(os.path.dirname(__file__), 'database.db'))

@app.before_request
def setup():
    init_db(DB)

# ---------------------------------------------------------------------------------------------
# LOGIN 
# Read

@app.route("/login", methods=["GET", "POST"])
def login():
    if "user" in session:
        return redirect(url_for("purchase"))

    with sqlite3.connect(DB) as conn:
        cur = conn.cursor()
        cur.execute("SELECT username FROM users")
        usernames = [row[0] for row in cur.fetchall()]

    selected_username = ""

    if request.method == "POST":
        selected_username = request.form.get("username", "").strip()
        passkey = request.form.get("passkey", "").strip()

        if not selected_username:
            flash("You must select a user.", "warning")
            return render_template("login.html", usernames=usernames, selected_username=selected_username)

        if len(passkey) != 6 or not passkey.isdigit():
            flash("Passkey must be exactly 6 digits.", "warning")
            return render_template("login.html", usernames=usernames, selected_username=selected_username)

        with sqlite3.connect(DB) as conn:
            cur = conn.cursor()
            cur.execute("SELECT id, passkey, role FROM users WHERE username=?", (selected_username,))
            user = cur.fetchone()

            if user and check_password_hash(user[1], passkey):
                session["user"] = selected_username
                session["role"] = user[2]
                session["user_id"] = user[0]
                return redirect(url_for("purchase"))
            else:
                flash("Invalid credentials", "warning")
                return render_template("login.html", usernames=usernames, selected_username=selected_username)

    return render_template("login.html", usernames=usernames, selected_username=selected_username)

# Global Funtions
def getProducts():
    category = request.args.get('category', 'all')
    try:
        with sqlite3.connect(DB) as conn:
            conn.row_factory = sqlite3.Row  
            cur = conn.cursor()
            if category == 'all':
                cur.execute("SELECT id, name, price, is_available, category FROM products WHERE is_deleted = 0")
            else:
                cur.execute("SELECT id, name, price, is_available, category FROM products WHERE category = ? AND is_deleted = 0", (category,))
            products = cur.fetchall()
    except sqlite3.Error as e:
        flash(f"An error occurred while fetching products: {e}", "warning")
        products = []

    if request.path == '/inventory':
        return render_template("inventory.html", products=products, selected_category=category)
    else:
        return render_template("purchase.html", products=products, selected_category=category)

# ---------------------------------------------------------------------------------------------
# LOGOUT 

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# ---------------------------------------------------------------------------------------------
# HOME 
# PURCHASE SECTION
# Create
# Read

@app.route("/")
@app.route("/home")
@app.route("/purchase", methods=["GET", "POST"])
@login_required
def purchase():
    if request.method == "POST":
        user_id = session.get("user_id")
        cash = float(request.form.get("cash_amount"))
        change = float(request.form.get("change"))
        total_amount = float(request.form.get("total_amount"))
        products = request.form.get("products")

        try:
            products_list = json.loads(products)
            with sqlite3.connect(DB) as conn:
                cur = conn.cursor()
                cur.execute("""
                    INSERT INTO transactions (user_id, cash, change, total_amount)
                    VALUES (?, ?, ?, ?)
                """, (user_id, cash, change, total_amount))
                transaction_id = cur.lastrowid

                for product in products_list:
                    cur.execute("""
                        INSERT INTO transaction_details (transaction_id, product_id, product_name, quantity, price_each, subtotal)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (transaction_id, product['id'], product['name'], product['quantity'], product['price'], product['subtotal']))

                conn.commit()
                flash("Transaction recorded successfully!", "success")
                return redirect(url_for('purchase')) 
        except sqlite3.Error as e:
            conn.rollback()
            flash(f"An error occurred while recording the transaction: {e}", "warning")
        except json.JSONDecodeError:
            flash("Invalid product data received.", "warning")

    return getProducts()

# ---------------------------------------------------------------------------------------------
# TRANSACTION RECORDS 
# Read
@app.route("/transactions")
@login_required
def transactions():
    return render_template("transactions.html")

# ---------------------------------------------------------------------------------------------
# INVENTORY MANAGEMENT 
# Create
# Read
# Update
# Delete

@app.route("/inventory")
@login_required
def inventory():
    return getProducts()

@app.route("/inventory/add", methods=["GET", "POST"])
@login_required
def add_product():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        price = request.form.get("price", "").strip()
        category = request.form.get("category", "").strip()
        is_available = request.form.get("is_available", "off") == "on"

        if not name or not price or not category:
            flash("All fields are required", "warning")
            return redirect(url_for("add_product"))

        try:
            price = float(price)
            if price <= 0:
                raise ValueError("Price must be greater than zero")
        except ValueError as e:
            flash(f"Price must be a valid positive number: {e}", "warning")
            return redirect(url_for("add_product"))

        try:
            with sqlite3.connect(DB) as conn:
                cur = conn.cursor()
                cur.execute("INSERT INTO products (name, price, is_available, category) VALUES (?, ?, ?, ?)",
                            (name, price, is_available, category))
                conn.commit()
            flash("Product added successfully", "success")
        except sqlite3.Error as e:
            flash(f"An error occurred while adding the product: {e}", "warning")
            return redirect(url_for("add_product"))

        return redirect(url_for("inventory"))

    return render_template("add_product.html")

@app.route("/inventory/edit/<int:product_id>", methods=["GET", "POST"])
@login_required
def edit_product(product_id):
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        price = request.form.get("price", "").strip()
        category = request.form.get("category", "").strip()
        is_available = request.form.get("is_available") == "on"

        if not name or not price or not category:
            flash("All fields are required", "warning")
            return redirect(url_for("inventory"))

        try:
            price = float(price)
            if price <= 0:
                raise ValueError("Price must be greater than zero")
        except ValueError as e:
            flash(f"Price must be a valid positive number: {e}", "warning")
            return redirect(url_for("inventory"))

        try:
            with sqlite3.connect(DB) as conn:
                cur = conn.cursor()
                cur.execute("""
                    UPDATE products 
                    SET name=?, price=?, is_available=?, category=? 
                    WHERE id=?""",
                    (name, price, is_available, category, product_id))
                conn.commit()
            flash("Product updated successfully", "success")
        except sqlite3.Error as e:
            flash(f"An error occurred while updating the product: {e}", "warning")
            return redirect(url_for("inventory"))

    return redirect(url_for("inventory"))

@app.route("/inventory/delete/<int:product_id>", methods=["POST"])
@login_required
def delete_product(product_id):
    try:
        with sqlite3.connect(DB) as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM products WHERE id=?", (product_id,))
            product = cur.fetchone()
            if not product:
                flash("Product not found", "warning")
                return redirect(url_for("inventory"))

            cur.execute("UPDATE products SET is_deleted = 1 WHERE id=?", (product_id,))
            conn.commit()
            flash("Product deleted successfully", "success")
    except sqlite3.Error as e:
        flash(f"An error occurred while deleting the product: {e}", "warning")
    return redirect(url_for("inventory"))

# ---------------------------------------------------------------------------------------------
# SALES RECORD 
# Read

@app.route("/sales")
@login_required
def sales():
    if not is_admin():
        return redirect(url_for("purchase"))
    
    return render_template("sales.html")

# ---------------------------------------------------------------------------------------------
# USER MANAGEMENT
# Create
# Read
# Update
# Delete

@app.route("/users")
@login_required
def users():
    if not is_admin():
        return redirect(url_for("purchase"))

    with sqlite3.connect(DB) as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, username, role FROM users")
        user_list = cur.fetchall()
    return render_template("users.html", users=user_list)

@app.route("/users/add", methods=["POST"])
@login_required
def add_user():
    if not is_admin():
        return redirect(url_for("purchase"))
    
    username = request.form["username"]
    passkey = request.form["passkey"]
    role = request.form["role"]

    if not username or not passkey or not role:
        flash("All fields are required", "warning")
        return redirect(url_for("users"))

    if not re.fullmatch(r"\d{6}", passkey):
        flash("Passkey must be exactly 6 digits", "warning")
        return redirect(url_for("users"))

    hashed_passkey = generate_password_hash(passkey)

    with sqlite3.connect(DB) as conn:
        cur = conn.cursor()
        cur.execute("INSERT INTO users (username, passkey, role) VALUES (?, ?, ?)",
                    (username, hashed_passkey, role))
        conn.commit()

    flash("User added successfully", "success")
    return redirect(url_for("users"))

@app.route("/users/edit/<int:user_id>", methods=["GET", "POST"])
@login_required
def edit_user(user_id):
    if not is_admin():
        return redirect(url_for("purchase"))
    
    with sqlite3.connect(DB) as conn:
        cur = conn.cursor()
        if request.method == "POST":
            username = request.form["username"]
            passkey = request.form["passkey"]
            role = request.form["role"]

            if not username or not role:
                flash("Username and role are required", "warning")
                return redirect(url_for("edit_user", user_id=user_id))

            if passkey:
                if not re.fullmatch(r"\d{6}", passkey):
                    flash("Passkey must be exactly 6 digits", "warning")
                    return redirect(url_for("edit_user", user_id=user_id))
                hashed_passkey = generate_password_hash(passkey)
                cur.execute("UPDATE users SET username=?, passkey=?, role=? WHERE id=?",
                            (username, hashed_passkey, role, user_id))
            else:
                cur.execute("UPDATE users SET username=?, role=? WHERE id=?",
                            (username, role, user_id))

            conn.commit()
            flash("User updated successfully", "success")
            return redirect(url_for("users"))
        else:
            cur.execute("SELECT id, username, role FROM users WHERE id=?", (user_id,))
            row = cur.fetchone()

    if row is None:
        flash("User not found", "warning")
        return redirect(url_for("users"))

    user_dict = {"id": row[0], "username": row[1], "role": row[2]}

    with sqlite3.connect(DB) as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, username, role FROM users")
        user_list = cur.fetchall()

    return render_template("users.html", users=user_list, edit_user=user_dict)

@app.route("/users/delete/<int:user_id>", methods=["POST"])
@login_required
def delete_user(user_id):
    if not is_admin():
        return redirect(url_for("purchase"))
    
    with sqlite3.connect(DB) as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM users WHERE id=?", (user_id,))
        conn.commit()
    flash("User deleted successfully", "success")
    return redirect(url_for("users"))

if __name__ == "__main__":
    app.run(debug=True)
