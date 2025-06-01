from flask import Flask, render_template, request, redirect, session, url_for
from functools import wraps

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function

def is_admin():
    return session.get("role") == "admin"

def is_staff():
    return session.get("role") == "staff"
