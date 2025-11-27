from flask import Blueprint, session, request, render_template, jsonify, redirect, url_for
from automation_platform.database.models import Bot, User, BotAssignment, Organization, BotExecution
from automation_platform.database.database import db
from automation_platform.auth.middleware import login_required, admin_required
from sqlalchemy import func, desc
from sqlalchemy.orm import relationship, joinedload
from datetime import datetime
from pathlib import Path
import os

schedule_reports_bp = Blueprint('schedule_reports_bp', __name__)


def format_datetime_fields(dt: datetime | None) -> tuple[str | None, str | None]:
    """
    Formats a datetime object into separate (date, time) strings.
    Returns (None, None) if the input is None.
    Date format: YYYY-MM-DD
    Time format: HH:MM:SS (No 'Z' suffix)
    """
    if dt is None:
        return None, None
    # Date in YYYY-MM-DD format
    date_str = dt.strftime("%Y-%m-%d")
    # Time in HH:MM:SS format, without the 'Z' suffix
    time_str = dt.strftime("%H:%M:%S")
    return date_str, time_str


@schedule_reports_bp.route("/bot-executions", methods=["GET"])
@login_required
def get_all_bot_execution_details():
    """
    Fetches detailed information for ALL BotExecutions, splitting started_at and completed_at 
    into separate date and time fields (without seconds), and excluding scheduled_at.
    """
    try:
        # Use joinedload to fetch Bot and User data in a single, efficient query (one JOIN).
        executions = db.session.query(BotExecution).options(
            joinedload(BotExecution.bot),
            joinedload(BotExecution.triggered_by_user)
        ).all()

        if not executions:
            # Return an empty list if no executions are found
            return jsonify([]), 200

        # Compile the required data structure for every execution
        results = []
        for execution in executions:
            
            # Format started_at and completed_at into separate date/time strings
            started_date, started_time = format_datetime_fields(execution.started_at)
            completed_date, completed_time = format_datetime_fields(execution.completed_at)

            execution_info = {
                "execution_id": execution.execution_id,
                # Data from Bot relationship
                "bot_name": execution.bot.bot_name,
                # Data from User relationship (or None if triggered_by_user_id is NULL)
                "triggered_by_user": execution.triggered_by_user.name if execution.triggered_by_user else "System/Scheduled",
                # Data from BotExecution itself
                "status": execution.status.value,
                
                # Split started_at
                "started_date": started_date,
                "started_time": started_time,
                
                # Split completed_at
                "completed_date": completed_date,
                "completed_time": completed_time,
            }
            # Note: scheduled_at is intentionally excluded here

            results.append(execution_info)

        return jsonify(results), 200

    except Exception as e:
        # Note: In a production app, logging the full traceback is better, but this handles the API response.
        print(f"Error fetching all bot execution details: {e}")
        return jsonify({
            "error": "Internal Server Error",
            "message": "An unexpected error occurred while processing the request."
        }), 500



@schedule_reports_bp.route("/reports_page", methods=["GET"])
@login_required
def get_page():
    return render_template("schedule_reports.html")


@schedule_reports_bp.route("/schedule_manager_page", methods=["GET"])
@login_required
def get_manager_page():
    return render_template("schedule_manager.html")