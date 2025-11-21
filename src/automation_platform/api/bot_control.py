from flask import Blueprint, session, request, render_template, jsonify, redirect, url_for
from automation_platform.database.models import Bot, User, BotAssignment, Organization, BotExecution
from automation_platform.database.database import db
from automation_platform.auth.middleware import login_required, admin_required
from sqlalchemy import func, desc
from pathlib import Path
import os

bot_control_api = Blueprint('bot_control_api', __name__)


@bot_control_api.route("/bot-control", methods=["GET", "POST"])
@login_required
def bot_control():
    current_user_id = session.get("user", {}).get("id")
    user = db.session.query(User).get(current_user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    # -----------------------------------
    # USER MUST BE ACTIVE
    # -----------------------------------
    if not user.is_active:
        return jsonify({"error": "User account is inactive."}), 403

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

    if org_id:
        org_id = int(org_id)
        org = db.session.query(Organization).get(org_id)

        if user.is_admin:
            # Admin sees all bots in the org
            bots_query = db.session.query(Bot).filter_by(organization_id=org_id)
        else:
            # Non-admin sees only bots assigned to them
            bots_query = (
                db.session.query(Bot)
                .join(BotAssignment, Bot.bot_id == BotAssignment.bot_id)
                .filter(
                    Bot.organization_id == org_id,
                    BotAssignment.user_id == current_user_id
                )
            )

        bots = bots_query.all()

        # Add last execution info
        bots_with_last_run = []
        for bot in bots:
            last_exec = (
                db.session.query(BotExecution)
                .filter(BotExecution.bot_id == bot.bot_id)
                .order_by(desc(BotExecution.created_at))
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

    # No org_id → show org selection
    return render_template("bot-control.html", page_title="Bot Control")




@bot_control_api.route("/bot-control-orgs", methods=["GET"])
@login_required
def get_organizations():
    current_user_id = session.get("user", {}).get("id")
    user = db.session.query(User).get(current_user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    # -----------------------------------
    # USER MUST BE ACTIVE
    # -----------------------------------
    if not user.is_active:
        return jsonify({"error": "User account is inactive."}), 403

    # -----------------------------------
    # ADMIN → sees ALL organizations
    # -----------------------------------
    if user.is_admin:
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

    # -----------------------------------
    # NON-ADMIN → sees ONLY their organization
    # -----------------------------------
    else:
        results = (
            db.session.query(
                Organization.organization_id.label("id"),
                Organization.organization_name.label("name"),
                func.count(Bot.bot_id).label("bot_count")
            )
            .outerjoin(Bot, Bot.organization_id == Organization.organization_id)
            .filter(Organization.organization_id == user.organization_id)
            .group_by(Organization.organization_id)
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



@bot_control_api.route("/bot-control/logs", methods=["GET", "POST"])
@login_required
def bot_logs_page():
    bot_id = None
    if request.method == "POST":
        bot_id = request.form.get("bot_id")
    
    # If GET, optionally you can redirect or show a message
    if not bot_id:
        return "Bot ID missing", 400

    return render_template("bot-control-logs.html", bot_id=bot_id)


@bot_control_api.route("/bot-wise-logs", methods=["POST"])
@login_required
def get_bot_logs():
    data = request.get_json(silent=True)
    if not data or "bot_id" not in data:
        return jsonify({"error": "bot_id is required"}), 400

    bot_id = data["bot_id"]

    # Fetch bot from DB
    bot = db.session.query(Bot).get(bot_id)
    if not bot:
        return jsonify({"error": "Bot not found"}), 404

    # Check log file path
    log_file_path = bot.log_file_path
    log_file = Path(log_file_path) if log_file_path else None

    content = ""
    if log_file and log_file.exists():
        with log_file.open("r", encoding="utf-8") as f:
            content = f.read()
    else:
        content = "Log file not found"

    return jsonify({
        "bot_id": bot_id,
        "logs": content,
        "is_active": bot.is_active   # <-- return active status
    })



@bot_control_api.route("/set-status", methods=["POST"])
@admin_required
def set_bot_status():
    data = request.get_json() or {}
    bot_id = data.get("bot_id")
    activate = data.get("activate")  # Expect True or False

    if bot_id is None or activate is None:
        return jsonify({"error": "Bot ID and 'activate' flag are required"}), 400

    bot = db.session.query(Bot).filter_by(bot_id=bot_id).first()
    if not bot:
        return jsonify({"error": "Bot not found"}), 404

    # Set status explicitly
    bot.is_active = bool(activate)

    try:
        db.session.commit()
        status_str = "activated" if bot.is_active else "deactivated"
        return jsonify({
            "message": f"Bot {status_str} successfully",
            "bot_id": bot.bot_id,
            "is_active": bot.is_active
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500
    



# --- API Route 1: Fetch all active Organizations ---
@bot_control_api.route('/organizations', methods=['GET'])
# @admin_required # Uncomment if needed
def get_model_organizations():
    # 1. Get bot_id from query parameters
    bot_id = request.args.get('bot_id', type=int)

    if not bot_id:
        return jsonify({"error": "Missing bot ID"}), 400

    try:
        # 2. Query to find the Bot and join its Organization
        # We look for the organization that matches the bot's organization_id
        result = db.session.execute(
            db.select(Organization.organization_id, Organization.organization_name)
            .join(Bot, Bot.organization_id == Organization.organization_id)
            .filter(Bot.bot_id == bot_id, Organization.is_active == True)
        ).first() # Use .first() since a bot belongs to only one organization

        org_list = []
        if result:
            org_id, org_name = result
            # 3. Format the single result as a list for the frontend
            org_list.append({"id": org_id, "name": org_name})
        
        # NOTE: If the bot is not found or its organization is inactive, org_list will be empty.
        
        return jsonify({"organizations": org_list}), 200
    except Exception as e:
        print(f"Error fetching organization for bot {bot_id}: {e}")
        return jsonify({"error": "Failed to load organizations."}), 500
    

# --- API Route 2: Fetch active Users based on Organization ID ---
@bot_control_api.route('/users', methods=['POST'])
# @admin_required # Uncomment if needed
def get_users_by_organization():
    data = request.get_json()
    org_id = data.get('organization_id')

    if not org_id:
        return jsonify({"error": "Missing organization ID"}), 400

    try:
        # Fetch active users belonging to the specified organization
        users = db.session.execute(
            db.select(User.user_id, User.name)
            .filter(User.organization_id == org_id, User.is_active == True)
            .order_by(User.name)
        ).all()

        # Format results
        user_list = [
            {"id": user_id, "name": user_name}
            for user_id, user_name in users
        ]
        
        return jsonify({"users": user_list}), 200
    except Exception as e:
        print(f"Error fetching users: {e}")
        return jsonify({"error": "Failed to load users for the organization."}), 500
