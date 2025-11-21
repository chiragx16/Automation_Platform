from flask import Blueprint, render_template, redirect, request, session, url_for
from automation_platform.auth.msal_client import msal_app, SCOPES, REDIRECT_URI
from automation_platform.database.models import User
from automation_platform.database.database import db

auth_bp = Blueprint("auth", __name__)

# -----------------------------
# LOGIN PAGE
# -----------------------------
@auth_bp.route("/login")
def login_page():
    if "user" in session:
        return redirect(url_for("index"))
    return render_template("login.html")


# -----------------------------
# LOCAL AUTH
# -----------------------------
@auth_bp.route("/login/local", methods=["POST"])
def login_local():
    email = request.form.get("email")
    password = request.form.get("password")
    org_id = request.form.get("organization_id", type=int)

    if not (email and password and org_id):
        return "Missing email, password, or organization", 400

    # Fetch ALL rows for this email (all org memberships)
    user_rows = (
        db.session.query(User)
        .filter(User.email == email, User.is_active == 1)
        .all()
    )

    if not user_rows:
        return "Invalid credentials", 401

    # Check if user is admin in any org
    admin_user = next((u for u in user_rows if u.is_admin), None)

    if admin_user:
        # Admin can log in to any org
        user_for_org = admin_user
    else:
        # Non-admin must belong to the selected org
        user_for_org = next((u for u in user_rows if u.organization_id == org_id), None)
        if not user_for_org:
            return "User not allowed in this organization", 403

    # Validate password
    if not user_for_org.verify_password(password):
        return "Invalid credentials", 401

    # Build session
    session.permanent = True
    session["user"] = {
        "id": user_for_org.user_id,
        "email": user_for_org.email,
        "name": user_for_org.name,
        "current_org_id": org_id,
        "is_admin": user_for_org.is_admin,
    }

    return redirect(url_for("index"))





# -----------------------------
# MICROSOFT LOGIN
# -----------------------------
@auth_bp.route("/login/microsoft", methods=["POST"])
def login_microsoft():
    org_id = request.form.get("organization_id", type=int)
    if not org_id:
        return "Organization is required", 400

    session["selected_org_id"] = org_id

    auth_url = msal_app.get_authorization_request_url(
        SCOPES,
        redirect_uri=REDIRECT_URI,
    )

    return redirect(auth_url)



# -----------------------------
# MICROSOFT CALLBACK
# -----------------------------
@auth_bp.route("/auth/callback")
def auth_callback():
    code = request.args.get("code")
    if not code:
        return "No code received", 400

    token_result = msal_app.acquire_token_by_authorization_code(
        code,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI,
    )

    if "id_token_claims" not in token_result:
        return f"Token error: {token_result}", 400

    claims = token_result["id_token_claims"]
    email = claims.get("preferred_username")

    # Fetch ALL rows for this email (all org memberships)
    user_rows = (
        db.session.query(User)
        .filter(User.email == email, User.is_active == 1)
        .all()
    )

    if not user_rows:
        return "You are not authorized to use this system.", 403

    # Organization selected at login (stored earlier)
    selected_org = session.pop("selected_org_id", None)
    if selected_org is None:
        return "Organization selection missing.", 400

    # Check if user is admin in any org
    admin_user = next((u for u in user_rows if u.is_admin), None)

    if admin_user:
        # Admin can log in to any org
        user_for_org = admin_user
    else:
        # Normal user must belong to selected org
        user_for_org = next((u for u in user_rows if u.organization_id == selected_org), None)
        if not user_for_org:
            return "You do not belong to the selected organization.", 403

    # Build session
    session.permanent = True
    session["user"] = {
        "id": user_for_org.user_id,
        "email": user_for_org.email,
        "name": user_for_org.name,
        "current_org_id": selected_org,
        "is_admin": user_for_org.is_admin,
    }

    return redirect(url_for("index"))





# -----------------------------
# LOGOUT
# -----------------------------
@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login_page"))
