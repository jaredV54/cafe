from flask import Flask, render_template, redirect, url_for, session, request, flash
from auth import login_required, is_admin, init_db
import sqlite3
import re 

app = Flask(__name__)
app.secret_key = 'secret'

DB = 'database.db'

@app.before_request
def setup():
    init_db(DB)

# ---------------------------------------------------------------------------------------------
# LOGIN 
# Read

@app.route("/login", methods=["GET", "POST"])
def login():
    if "user" in session:
        return redirect(url_for("home"))
    
    if request.method == "POST":
        username = request.form["username"]
        passkey = request.form["passkey"]
        with sqlite3.connect(DB) as conn:
            cur = conn.cursor()
            cur.execute("SELECT id, role FROM users WHERE username=? AND passkey=?", (username, passkey))
            user = cur.fetchone()
            if user:
                session["user"] = username
                session["role"] = user[1]
                session["user_id"] = user[0]
                return redirect(url_for("home"))
            else:
                flash("Invalid credentials", "danger")
    else:
        with sqlite3.connect(DB) as conn:
            cur = conn.cursor()
            cur.execute("SELECT username FROM users")
            usernames = [row[0] for row in cur.fetchall()]
        return render_template("login.html", usernames=usernames)
    
    return render_template("login.html", usernames=[])  

# ---------------------------------------------------------------------------------------------
# LOGOUT 

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# ---------------------------------------------------------------------------------------------
# HOME 
# TRANSACTION MAKER
# Create
# Read

@app.route("/")
@login_required
def home():
    return render_template("home.html")

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
    return render_template("inventory.html")

# ---------------------------------------------------------------------------------------------
# SALES RECORD 
# Read

@app.route("/sales")
@login_required
def inventory():
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
        return redirect(url_for("home"))

    with sqlite3.connect(DB) as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, username, role FROM users")
        user_list = cur.fetchall()
    return render_template("users.html", users=user_list)

@app.route("/users/add", methods=["POST"])
@login_required
def add_user():
    if not is_admin():
        return redirect(url_for("home"))
    
    username = request.form["username"]
    passkey = request.form["passkey"]
    role = request.form["role"]

    if not username or not passkey or not role:
        flash("All fields are required", "warning")
        return redirect(url_for("users"))

    if not re.fullmatch(r"\d{6}", passkey):
        flash("Passkey must be exactly 6 digits", "warning")
        return redirect(url_for("users"))

    with sqlite3.connect(DB) as conn:
        cur = conn.cursor()
        cur.execute("INSERT INTO users (username, passkey, role) VALUES (?, ?, ?)",
                    (username, passkey, role))
        conn.commit()

    flash("User added successfully", "success")
    return redirect(url_for("users"))

@app.route("/users/edit/<int:user_id>", methods=["GET", "POST"])
@login_required
def edit_user(user_id):
    if not is_admin():
        return redirect(url_for("home"))
    
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
                cur.execute("UPDATE users SET username=?, passkey=?, role=? WHERE id=?",
                            (username, passkey, role, user_id))
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
        return redirect(url_for("home"))
    
    with sqlite3.connect(DB) as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM users WHERE id=?", (user_id,))
        conn.commit()
    flash("User deleted successfully", "success")
    return redirect(url_for("users"))

if __name__ == "__main__":
    app.run(debug=True)
