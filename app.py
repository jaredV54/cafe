from flask import Flask, render_template, redirect, url_for, session
from auth import login_required
import sqlite3

app = Flask(__name__)
app.secret_key = 'your_secret_key'

@app.route("/")
@login_required
def home():
    return render_template("pos.html")

@app.route("/transactions")
@login_required
def transactions():
    return render_template("transactions.html")

@app.route("/inventory")
@login_required
def inventory():
    return render_template("inventory.html")

@app.route("/users")
@login_required
def users():
    return render_template("users.html")

@app.route("/sales")
@login_required
def sales():
    return render_template("sales.html")

if __name__ == "__main__":
    app.run(debug=True)
