from flask import Flask, render_template, redirect, url_for, session, request, flash, jsonify
from auth import login_required, is_admin, init_db
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import json
import re
from dotenv import load_dotenv
import os
from datetime import datetime

load_dotenv()  

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'secret')  

DB = os.getenv('DATABASE_URL', 'database.db')
# When deployed
# DB = os.getenv('DATABASE_URL', os.path.join(os.path.dirname(__file__), 'database.db'))

@app.before_request
def setup():
    init_db(DB)

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
# LOGIN 
# Read
@app.route("/login", methods=["GET", "POST"])
def login():
    if "user" in session:
        return redirect(url_for("purchase"))

    with sqlite3.connect(DB) as conn:
        cur = conn.cursor()
        cur.execute("SELECT username FROM users WHERE is_deleted != 1")
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
        mode_of_payment = request.form.get("mode_of_payment", "cash")
        products = request.form.get("products")

        try:
            products_list = json.loads(products)
            with sqlite3.connect(DB) as conn:
                cur = conn.cursor()
                cur.execute("""
                    INSERT INTO transactions (user_id, cash, change, total_amount, mode_of_payment)
                    VALUES (?, ?, ?, ?, ?)
                """, (user_id, cash, change, total_amount, mode_of_payment))
                transaction_id = cur.lastrowid

                for product in products_list:
                    cur.execute("""
                        INSERT INTO transaction_details (transaction_id, product_id, product_name, quantity, price_each, subtotal)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (transaction_id, product['id'], product['name'], product['quantity'], product['price'], product['subtotal']))

                conn.commit()
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify(success=True, receipt_id=transaction_id)
                flash("Transaction recorded successfully!", "success")
                return redirect(url_for('purchase')) 
        except sqlite3.Error as e:
            conn.rollback()
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify(success=False, message=f"An error occurred while recording the transaction: {e}")
            flash(f"An error occurred while recording the transaction: {e}", "warning")
        except json.JSONDecodeError:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify(success=False, message="Invalid product data received.")
            flash("Invalid product data received.", "warning")

    return getProducts()

# ---------------------------------------------------------------------------------------------
# TRANSACTION RECORDS 
# Read
@app.route('/transactions', methods=['GET', 'POST'])
@login_required
def transactions():
    q = request.args.get('q')
    startdate = request.args.get('startdate')
    enddate = request.args.get('enddate')
    receipt_id = request.args.get('receipt_id')  

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    transaction = None
    products = []

    if receipt_id:
        cursor.execute("""
            SELECT transactions.id AS transaction_id, transactions.*, users.username, users.id AS user_id 
            FROM transactions 
            INNER JOIN users ON transactions.user_id = users.id
            WHERE transactions.id = ? AND transactions.is_deleted != 1
        """, (receipt_id,))
        transaction = cursor.fetchone()

        if transaction:
            cursor.execute("""
                SELECT product_name, quantity, price_each AS price, subtotal
                FROM transaction_details
                WHERE transaction_id = ?
            """, (receipt_id,))
            products = cursor.fetchall()
            transaction = list(transaction)
            transaction[4] = f"{float(transaction[4]):.2f}"  
            transaction[5] = f"{float(transaction[5]):.2f}"  
            transaction[6] = f"{float(transaction[6]):.2f}" 

    if startdate and enddate:
        try:
            start_dt = datetime.strptime(startdate, '%Y-%m-%dT%H:%M')
            end_dt = datetime.strptime(enddate, '%Y-%m-%dT%H:%M')
            if end_dt < start_dt:
                flash("End date/time cannot be before start date/time.", "warning")
                return redirect(url_for('transactions'))
            start_datetime_str = start_dt.strftime('%Y-%m-%d %H:%M:%S')
            end_datetime_str = end_dt.strftime('%Y-%m-%d %H:%M:%S')
        except ValueError:
            flash("Invalid date/time format.", "warning")
            return redirect(url_for('transactions'))

        cursor.execute("""
            SELECT transactions.id AS transaction_id, transactions.*, users.username, users.id AS user_id 
            FROM transactions 
            INNER JOIN users ON transactions.user_id = users.id
            WHERE transaction_time BETWEEN ? AND ? AND transactions.is_deleted != 1
            ORDER BY transactions.id DESC
        """, (start_datetime_str, end_datetime_str))
        transactions = cursor.fetchall()

    elif q:
        try:
            if q.strip().isdigit():
                transaction_id = int(q.strip())
                cursor.execute("""
                    SELECT transactions.id AS transaction_id, transactions.*, users.username, users.id AS user_id 
                    FROM transactions 
                    INNER JOIN users ON transactions.user_id = users.id
                    WHERE transactions.id = ? AND transactions.is_deleted != 1
                    ORDER BY transactions.id DESC
                """, (transaction_id,))
                transactions = cursor.fetchall()
                if not transactions:
                    flash(f"Transaction ID '{q}' not found", "warning")
            else:
                q_lower = q.strip().lower()
                cursor.execute("""
                    SELECT transactions.id AS transaction_id, transactions.*, users.username, users.id AS user_id 
                    FROM transactions 
                    INNER JOIN users ON transactions.user_id = users.id
                    WHERE LOWER(users.username) LIKE ? AND transactions.is_deleted != 1
                    ORDER BY transactions.id DESC
                """, (f"%{q_lower}%",))
                transactions = cursor.fetchall()
                if not transactions:
                    flash(f"Username '{q}' not found", "warning")
        except Exception as e:
            flash(f"An error occurred: {str(e)}", "danger")
            transactions = []

    else:
        cursor.execute("""
            SELECT transactions.id AS transaction_id, transactions.*, users.username, users.id AS user_id
            FROM transactions 
            INNER JOIN users ON transactions.user_id = users.id
            WHERE transactions.is_deleted != 1
            ORDER BY transactions.id DESC
        """)
        transactions = cursor.fetchall()

    conn.close()

    formatted_transactions = []
    for t in transactions:
        transaction_time = datetime.strptime(t[3], '%Y-%m-%d %H:%M:%S')
        formatted_time = transaction_time.strftime('%Y-%m-%d %I:%M %p')  # Format to include AM/PM
        # Format cash, change, and total_amount to 2 decimal places
        formatted_transactions.append((
            t[0],                # transaction_id
            t[9],                # username
            formatted_time,      # formatted date
            f"{float(t[6]):.2f}",# total_amount
            f"{float(t[4]):.2f}",# cash
            f"{float(t[5]):.2f}",# change
            t[8]                 # mode_of_payment
        ))

    return render_template('transactions.html', transactions=formatted_transactions, transaction=transaction, products=products, q=q, startdate=startdate, enddate=enddate)

@app.route('/transactions/delete/<int:transaction_id>', methods=['POST'])
@login_required
def delete_transaction(transaction_id):
    if not is_admin():
        flash("Unauthorized action.", "danger")
        return redirect(url_for('transactions'))
    try:
        with sqlite3.connect(DB) as conn:
            cur = conn.cursor()
            cur.execute("UPDATE transactions SET is_deleted = 1 WHERE id=?", (transaction_id,))
            conn.commit()
        flash("Transaction deleted successfully.", "success")
    except sqlite3.Error as e:
        flash(f"An error occurred while deleting the transaction: {e}", "warning")
    return redirect(url_for('transactions'))

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
    print(f"Editing product with ID: {product_id}") 
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
            flash(f"{e}", "warning")
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

@app.route("/sales", methods=["GET"])
@login_required
def sales():
    if not is_admin():
        return redirect(url_for("purchase"))

    view = request.args.get("view", "daily")
    mop = request.args.get("mop", "all")

    today = datetime.now()
    weekday_map = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]

    from_date = to_date = today.strftime("%Y-%m-%d")
    from_month = to_month = today.strftime("%Y-%m")
    from_year = to_year = today.strftime("%Y")

    if view == "daily":
        from_date = request.args.get("from_date", from_date)
        to_date = request.args.get("to_date", to_date)
        try:
            from_dt = datetime.strptime(from_date, "%Y-%m-%d")
            to_dt = datetime.strptime(to_date, "%Y-%m-%d")
            if to_dt < from_dt:
                flash("End date cannot be before start date.", "warning")
                return redirect(url_for("sales", view=view, mop=mop))
        except ValueError:
            flash("Invalid date format.", "warning")
            return redirect(url_for("sales", view=view, mop=mop))
    elif view == "monthly":
        from_month = request.args.get("from_month", from_month)
        to_month = request.args.get("to_month", to_month)
        try:
            from_dt = datetime.strptime(from_month, "%Y-%m")
            to_dt = datetime.strptime(to_month, "%Y-%m")
            if to_dt < from_dt:
                flash("End month cannot be before start month.", "warning")
                return redirect(url_for("sales", view=view, mop=mop))
        except ValueError:
            flash("Invalid month format.", "warning")
            return redirect(url_for("sales", view=view, mop=mop))
    elif view == "yearly":
        from_year = request.args.get("from_year", from_year)
        to_year = request.args.get("to_year", to_year)
        try:
            from_yr = int(from_year)
            to_yr = int(to_year)
            if to_yr < from_yr:
                flash("End year cannot be before start year.", "warning")
                return redirect(url_for("sales", view=view, mop=mop))
        except ValueError:
            flash("Invalid year format.", "warning")
            return redirect(url_for("sales", view=view, mop=mop))

    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    daily_data = []
    monthly_data = []
    yearly_data = []
    total_revenue = 0

    if view == "daily":
        if mop == "all":
            params = [from_date, to_date]
            cur.execute("""
                SELECT 
                    strftime('%w', transaction_time) as weekday,
                    strftime('%Y-%m-%d', transaction_time) as date,
                    SUM(total_amount)
                FROM transactions
                WHERE is_deleted != 1 AND date(transaction_time) BETWEEN ? AND ?
                GROUP BY date
                ORDER BY date DESC
            """, params)
            daily_data = cur.fetchall()
            total_revenue = sum(row[2] for row in daily_data)
        else:
            params = [from_date, to_date, mop]
            cur.execute("""
                SELECT 
                    strftime('%w', transaction_time) as weekday,
                    strftime('%Y-%m-%d', transaction_time) as date,
                    mode_of_payment,
                    SUM(total_amount)
                FROM transactions
                WHERE is_deleted != 1 AND date(transaction_time) BETWEEN ? AND ? AND mode_of_payment = ?
                GROUP BY date, mode_of_payment
                ORDER BY date DESC
            """, params)
            daily_data = cur.fetchall()
            total_revenue = sum(row[3] for row in daily_data)

    elif view == "monthly":
        if mop == "all":
            params = [from_month, to_month]
            cur.execute("""
                SELECT 
                    strftime('%Y-%m', transaction_time) as month,
                    SUM(total_amount)
                FROM transactions
                WHERE is_deleted != 1 AND strftime('%Y-%m', transaction_time) BETWEEN ? AND ?
                GROUP BY month
                ORDER BY month DESC
            """, params)
            monthly_data = cur.fetchall()
            total_revenue = sum(row[1] for row in monthly_data)
        else:
            params = [from_month, to_month, mop]
            cur.execute("""
                SELECT 
                    strftime('%Y-%m', transaction_time) as month,
                    mode_of_payment,
                    SUM(total_amount)
                FROM transactions
                WHERE is_deleted != 1 AND strftime('%Y-%m', transaction_time) BETWEEN ? AND ? AND mode_of_payment = ?
                GROUP BY month, mode_of_payment
                ORDER BY month DESC
            """, params)
            monthly_data = cur.fetchall()
            total_revenue = sum(row[2] for row in monthly_data)

    elif view == "yearly":
        if mop == "all":
            params = [from_year, to_year]
            cur.execute("""
                SELECT 
                    strftime('%Y', transaction_time) as year,
                    SUM(total_amount)
                FROM transactions
                WHERE is_deleted != 1 AND strftime('%Y', transaction_time) BETWEEN ? AND ?
                GROUP BY year
                ORDER BY year DESC
            """, params)
            yearly_data = cur.fetchall()
            total_revenue = sum(row[1] for row in yearly_data)
        else:
            params = [from_year, to_year, mop]
            cur.execute("""
                SELECT 
                    strftime('%Y', transaction_time) as year,
                    mode_of_payment,
                    SUM(total_amount)
                FROM transactions
                WHERE is_deleted != 1 AND strftime('%Y', transaction_time) BETWEEN ? AND ? AND mode_of_payment = ?
                GROUP BY year, mode_of_payment
                ORDER BY year DESC
            """, params)
            yearly_data = cur.fetchall()
            total_revenue = sum(row[2] for row in yearly_data)

    conn.close()

    return render_template(
        "sales.html",
        view=view,
        mop=mop,
        from_date=from_date,
        to_date=to_date,
        from_month=from_month,
        to_month=to_month,
        from_year=from_year,
        to_year=to_year,
        daily_data=daily_data,
        monthly_data=monthly_data,
        yearly_data=yearly_data,
        total_revenue=total_revenue,
        weekday_map=weekday_map
    )

# ---------------------------------------------------------------------------------------------
# USER MANAGEMENT
# Create
# Read
# Update
# Delete

@app.route("/users")
def users():
    """ if not is_admin():
        return redirect(url_for("purchase")) """
    
    with sqlite3.connect(DB) as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, username, role FROM users WHERE is_deleted != 1")
        user_list = cur.fetchall()
    return render_template("users.html", users=user_list)

@app.route("/users/add", methods=["POST"])
def add_user():
    """ if not is_admin():
        return redirect(url_for("purchase")) """
    
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
def edit_user(user_id):
    """ if not is_admin():
        return redirect(url_for("purchase")) """
    
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
def delete_user(user_id):
    """ if not is_admin():
        return redirect(url_for("purchase")) """
    
    with sqlite3.connect(DB) as conn:
        cur = conn.cursor()
        cur.execute("UPDATE users SET is_deleted = 1 WHERE id=?", (user_id,))
        conn.commit()
    flash("User deleted successfully", "success")
    return redirect(url_for("users"))

if __name__ == "__main__":
    app.run(debug=True)
