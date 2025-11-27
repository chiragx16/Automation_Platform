from flask import Blueprint, session, request, render_template, jsonify, redirect, url_for
from automation_platform.database.models import *
from automation_platform.database.database import db
from automation_platform.auth.middleware import login_required, admin_required
from sqlalchemy import func, desc
from sqlalchemy.orm import relationship, joinedload
from datetime import datetime
from pathlib import Path
import os, requests

bot_reports_bp = Blueprint('bot_reports_bp', __name__)


@bot_reports_bp.route("/bot_reports_page", methods=["GET"])
@login_required
def bot_reports_page():
    return render_template("bot_reports.html")


# NEW ROUTE for the separate log view page
@bot_reports_bp.route("/view_log_table/<int:source_id>", methods=["GET"])
@login_required
def view_log_table(source_id):
    # This renders the new template. The source_id is available in the URL
    # and can be used by the new log_view.js script.
    return render_template("bot_reports_log_view.html", source_id=source_id)


@bot_reports_bp.route("/with-log-sources", methods=["GET"])
@login_required
def get_bots_with_log_sources():
    # Get logged-in user
    user_id = session.get("user", {}).get("id")
    user = User.query.filter_by(user_id=user_id).first()

    if not user:
        return jsonify({"message": "User not found"}), 404

    # Base query: we want BotLogSource, joined with Bot,
    # but only for active bots
    query = (
        db.session.query(BotLogSource)
        .join(Bot, Bot.bot_id == BotLogSource.bot_id)
        .filter(Bot.is_active == True)
    )

    # If not admin -> restrict to user's organization
    if not user.is_admin:
        query = query.filter(Bot.organization_id == user.organization_id)

    log_sources = query.all()

    # Format response
    result = [
        {
            "id": src.id,
            "display_name": src.display_name,
            "bot_id": src.bot_id,          # optional but useful
            "bot_name": src.bot.bot_name   # optional if you want context
        }
        for src in log_sources
    ]

    return jsonify(result), 200



@bot_reports_bp.route("/show-custom-table", methods=["GET"])
@login_required
def fetch_log_source_data():
    source_id = request.args.get("source_id")

    if not source_id:
        return jsonify({"error": "source_id is required"}), 400

    source = BotLogSource.query.filter_by(id=source_id).first()
    if not source:
        return jsonify({"error": "Log source not found"}), 404

    full_url = source.endpoint_path.strip()

    try:
        response = requests.get(full_url, timeout=10)

        if not response.ok:
            response_data = f"External endpoint returned HTTP Error {response.status_code}: {response.reason}"
            columns = []
        else:
            try:
                response_data = response.json()  # Expect a list of dicts
                # Extract columns in the order they appear in the first dict
                if isinstance(response_data, list) and len(response_data) > 0 and isinstance(response_data[0], dict):
                    columns = list(response_data[0].keys())   # <-- ORDER PRESERVED HERE
                else:
                    columns = []
            except requests.exceptions.JSONDecodeError:
                response_data = f"External endpoint returned non-JSON data: {response.text[:200]}..."
                columns = []

    except requests.exceptions.RequestException as e:
        response_data = f"Connection error calling external endpoint: {str(e)}"
        columns = []

    return jsonify({
        "log_source_id": source.id,
        "display_name": source.display_name,
        "endpoint": full_url,
        "columns": columns,       # <-- NEW FIELD
        "data": response_data
    }), 200

