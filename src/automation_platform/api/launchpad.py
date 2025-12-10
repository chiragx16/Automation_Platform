from flask import Blueprint, session, request, render_template, jsonify, redirect, url_for
from automation_platform.database.models import Bot, User, BotAssignment, Organization, BotExecution
from automation_platform.database.database import db
from automation_platform.auth.middleware import login_required, admin_required
from sqlalchemy import func, desc
from pathlib import Path
import os

launchpad_bp = Blueprint('launchpad_bp', __name__)

@launchpad_bp.route("/launch-pad")
@login_required
def launchpad():
    current_user_id = session.get("user", {}).get("id")
    user = db.session.query(User).get(current_user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    # -----------------------------------
    # USER MUST BE ACTIVE
    # -----------------------------------
    if not user.is_active:
        return jsonify({"error": "User account is inactive."}), 403

    # Fetch only active users
    user_obj = db.session.query(User).filter_by(user_id=current_user_id, is_active=True).first()
    if not user_obj:
        return "Your account is inactive.", 403

    orgs_query = db.session.query(Organization)

    # For non-admins, only include orgs the user belongs to
    if not user.is_admin:
        orgs_query = orgs_query.filter(Organization.organization_id == user_obj.organization_id)

    orgs = orgs_query.all()
    data = []

    for org in orgs:
        if user.is_admin:
            bots = org.bots  # all bots in org
        else:
            # Only bots assigned to the current user
            bots = (
                db.session.query(Bot)
                .join(BotAssignment, Bot.bot_id == BotAssignment.bot_id)
                .filter(
                    Bot.organization_id == org.organization_id,
                    BotAssignment.user_id == current_user_id
                )
                .all()
            )

        # Sort bots: active first, then by name
        sorted_bots = sorted(bots, key=lambda b: (not b.is_active, b.bot_name.lower()))

        bots_data = []
        for bot in sorted_bots:
            # Get last execution
            last_exec = (
                db.session.query(BotExecution)
                .filter(BotExecution.bot_id == bot.bot_id)
                .order_by(desc(BotExecution.created_at))
                .first()
            )

            bots_data.append({
                "id": bot.bot_id,
                "name": bot.bot_name,
                "status": bot.is_active,
                "last_run": last_exec.completed_at if last_exec and last_exec.completed_at else (
                            last_exec.started_at if last_exec else None)
            })

        data.append({
            "id": org.organization_id,
            "name": org.organization_name,
            "bots": bots_data
        })

    return render_template("launchpad.html", page_title="Launchpad", org_data=data)


 
@launchpad_bp.route("/bot-details", methods=["GET", "POST"])
@login_required
def bot_details_page():
    bot_id = request.form.get("bot_id")
    if not bot_id:
        return redirect(url_for('api.launchpad_bp.launchpad'))  # Redirect if no ID provided

    # Fetch bot
    bot = db.session.query(Bot).get(bot_id)
    if not bot:
        return "Bot not found", 404
    
    # Check if bot is active
    if not bot.is_active:
        return "This bot is inactive and cannot be accessed.", 403

    # Get category name safely
    category_name = bot.category.name if bot.category else "Uncategorized"

    return render_template(
        "bot-details.html",
        page_title=f"Details: {bot.bot_name}",
        bot_id=bot.bot_id,
        bot_name=bot.bot_name,
        bot_description=bot.description,
        org_name=bot.organization.organization_name if bot.organization else "N/A",
        category_name=category_name
    )