from flask import Blueprint, session, request, render_template, jsonify, redirect, url_for
from automation_platform.database.models import Bot, User, BotAssignment, Organization, BotExecution
from automation_platform.database.database import db
from automation_platform.auth.middleware import login_required, admin_required
from sqlalchemy import func, desc
from pathlib import Path
import os

home_bp = Blueprint('home_bp', __name__)

@home_bp.route('/')
@login_required
def home():
    return render_template("home.html")

@home_bp.route("/stats")
@login_required
def api_stats():

    total_bots = db.session.query(func.count(Bot.bot_id)).scalar()
    active_bots = db.session.query(func.count(Bot.bot_id)).filter(Bot.is_active == 1).scalar()
    total_users = db.session.query(func.count(User.user_id)).scalar()

    return jsonify({
        "total_bots": total_bots,
        "active_bots": active_bots,
        "total_users": total_users
    })


@home_bp.route("/latest_executions", methods=["GET"])
@login_required
def get_last_5_executions():
    executions = (
        BotExecution.query
        .order_by(BotExecution.created_at.desc())
        .limit(5)
        .all()
    )

    response = []
    for exe in executions:
        response.append({
            "bot_name": exe.bot.bot_name if exe.bot else None,
            "status": exe.status.value,
            "completed_at": str(exe.completed_at) if exe.completed_at else None
        })

    return jsonify(response)