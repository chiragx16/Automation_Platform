from flask import Blueprint, session, request, render_template, jsonify, redirect, url_for
from automation_platform.database.models import Bot, User, BotAssignment, Organization, BotExecution
from automation_platform.database.database import db
from automation_platform.auth.middleware import login_required, admin_required
from sqlalchemy import func, desc
from pathlib import Path
import os

bot_api = Blueprint('bot_api', __name__)

@bot_api.route("/check")
@login_required
def get_bots():

    user = session["user"]

    # Admin can see all bots regardless of organization or assignment
    if user["is_admin"]:
        bots = db.session.query(Bot).all()
        return {"bots": [b.bot_name for b in bots]}

    # Regular users: only bots assigned to them, inside their org
    current_org = user["current_org_id"]
    user_id = user["id"]
    print(user_id, current_org)

    bots = (
        db.session.query(Bot)
        .join(BotAssignment, Bot.bot_id == BotAssignment.bot_id)
        .filter(
            BotAssignment.user_id == user_id
        )
        .all()
    )

    return {"bots": [b.bot_name for b in bots]}



@bot_api.route("/adduser")
@admin_required
def addUser():

    u = User(
        name="Chirag",
        username="chirag2",
        email="chirag.modi@vc-erp.com",
        organization_id=2,
    )
    u.set_password("1234")

    db.session.add(u)
    db.session.commit()

    return {"status": "user created", "id": u.user_id}



@bot_api.route("/bot-control/logs", methods=["GET", "POST"])
def bot_logs_page():
    bot_id = None

    if request.method == "POST":
        bot_id = request.form.get("bot_id")
    
    # If GET, optionally you can redirect or show a message
    if not bot_id:
        return "Bot ID missing", 400

    return render_template("bot-control-logs.html", bot_id=bot_id)


@bot_api.route("/bot-wise-logs", methods=["POST"])
def get_bot_logs():
    data = request.get_json(silent=True)
    if not data or "bot_id" not in data:
        return jsonify({"error": "bot_id is required"}), 400

    bot_id = data["bot_id"]

    # Fetch bot from DB
    bot = db.session.query(Bot).get(bot_id)
    if not bot:
        return jsonify({"error": "Bot not found"}), 404

    # Use log_file_path from bot
    log_file_path = bot.log_file_path
    log_file = Path(log_file_path)  # converts string to Path object safely

    if not log_file.exists():
        return jsonify({"error": "Log file not found"}), 404

    with log_file.open("r", encoding="utf-8") as f:
        content = f.read()

    return jsonify({"bot_id": bot_id, "logs": content})




@bot_api.route("/bot-control", methods=["GET", "POST"])
def bot_control():

    org_id = None

    # If JSON body exists (POST)
    if request.is_json:
        data = request.get_json(silent=True) or {}
        org_id = data.get("org_id")

    # If form POST
    if request.method == "POST" and not request.is_json:
        org_id = request.form.get("org_id")

    # If GET with query parameter
    if not org_id:
        org_id = request.args.get("org_id")

    # Convert org_id to int if not None
    if org_id:
        org_id = int(org_id)

        org = db.session.query(Organization).get(org_id)

        # Get bots for this org
        bots = db.session.query(Bot).filter_by(organization_id=org_id).all()

        # Add last execution info
        bots_with_last_run = []
        for bot in bots:
            last_exec = (
                db.session.query(BotExecution)
                .filter(BotExecution.bot_id == bot.bot_id)
                .order_by(desc(BotExecution.created_at))  # or .started_at if preferred
                .first()
            )
            bots_with_last_run.append({
                "bot": bot,
                "last_execution": last_exec
            })

        return render_template(
            "bot-control-bots.html",
            page_title="Bot Control",
            org=org,
            bots=bots_with_last_run
        )

    # No org_id passed → show organization selection
    return render_template("bot-control.html", page_title="Bot Control")



from sqlalchemy import desc

@bot_api.route("/launchpad")
def launchpad():

    orgs = db.session.query(Organization).all()
    data = []

    for org in orgs:
        bots = org.bots  # lazy load bots

        # Sort bots: active first, then by name
        sorted_bots = sorted(bots, key=lambda b: (not b.is_active, b.bot_name.lower()))

        bots_data = []
        for bot in sorted_bots:
            # Get last execution if exists
            last_exec = (
                db.session.query(BotExecution)
                .filter(BotExecution.bot_id == bot.bot_id)
                .order_by(desc(BotExecution.created_at))  # or .started_at
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

 





# ✅ Get all organizations
@bot_api.route("/bot-control-orgs", methods=["GET"])
def get_organizations():
    # Query organizations + bot count

    results = (
        db.session.query(
            Organization.organization_id.label("id"),
            Organization.organization_name.label("name"),
            func.count(Bot.bot_id).label("bot_count")
        )
        .outerjoin(Bot, Bot.organization_id == Organization.organization_id)
        .group_by(Organization.organization_id)
        .order_by(Organization.organization_name)
        .all()
    )

    organizations = [
        {
            "id": row.id,
            "name": row.name,
            "bot_count": row.bot_count
        }
        for row in results
    ]

    return jsonify(organizations)



@bot_api.route("/stats")
def api_stats():

    total_bots = db.session.query(func.count(Bot.bot_id)).scalar()
    active_bots = db.session.query(func.count(Bot.bot_id)).filter(Bot.is_active == 1).scalar()
    total_users = db.session.query(func.count(User.user_id)).scalar()

    return jsonify({
        "total_bots": total_bots,
        "active_bots": active_bots,
        "total_users": total_users
    })



@bot_api.route("/bot-details", methods=["GET", "POST"])
def bot_details_page():
    bot_id = request.form.get("bot_id")
    if not bot_id:
        return redirect(url_for('api.bot_api.launchpad')) # Redirect if no ID provided
   
    # We need to fetch the bot and its organization
    bot = db.session.query(Bot).get(bot_id)
    if not bot:
        return "Bot not found", 404
 
    # The mock schedule must be hardcoded here for the new page
    schedule = "30 min - 1 hour"
   
    return render_template(
        "bot-details.html",
        page_title=f"Details: {bot.bot_name}",
        bot_id=bot.bot_id,
        bot_name=bot.bot_name,
        org_name=bot.organization.organization_name if bot.organization else "N/A"
        # last_run=bot.last_run.strftime("%Y-%m-%d %H:%M:%S") if bot.last_run else None,
        # schedule=schedule
    )