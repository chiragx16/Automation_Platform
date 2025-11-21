from flask import Blueprint, session, request, render_template, jsonify, redirect, url_for
from automation_platform.database.models import Bot, User, BotAssignment, Organization, BotExecution
from automation_platform.database.database import db
from automation_platform.auth.middleware import login_required, admin_required
from sqlalchemy import func, desc
from pathlib import Path
import os

home_api = Blueprint('home_api', __name__)

@home_api.route('/')
@login_required
def home():
    return render_template("home.html")

@home_api.route("/stats")
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
