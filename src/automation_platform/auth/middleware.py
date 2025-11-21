from functools import wraps
from flask import redirect, session, url_for

def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("auth.login_page"))
        return fn(*args, **kwargs)
    return wrapper


def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user = session.get("user")
        if not user:
            return redirect(url_for("auth.login_page"))
        if not user.get("is_admin"):
            return "Forbidden: Admins only.", 403
        return fn(*args, **kwargs)
    return wrapper
