from flask import Blueprint, jsonify
from automation_platform.database.models import *
from automation_platform.database.database import db

populate_bp = Blueprint("populate", __name__)

@populate_bp.route("/organizations", methods=["GET"])
def populate_organizations():
    # Example organizations
    orgs = [
        "VCERP Consulting Pvt. Ltd",
        "Arvind Limited",
        "Bikaji Foods International Limited",
        "Tara Paints Pvt Ltd"
    ]
    
    created_orgs = []
    for name in orgs:
        # Check if organization already exists to avoid duplicates
        existing = db.session.query(Organization).filter_by(organization_name=name).first()
        if not existing:
            org = Organization(organization_name=name)
            db.session.add(org)
            created_orgs.append(name)
    
    db.session.commit()
    
    return "Organizations added successfully"


@populate_bp.route("/users", methods=["GET"])
def populate_users():
    users_data = [
        # (name, email, password, organization_id, is_admin)
        # ("Chirag Modi", "chirag.modi@vc-erp.com", "1234", 1, True),
        ("Prince Tejani", "prince.tejani@vc-erp.com", "1234", 2, False),
        # ("Rahul Suthar", "rahul.suthar@vc-erp.com", "1234", 1, False),

        # ("Aishwarya Moksha", "aishwarya.moksha@arvind.com", "1234", 2, True),
        # ("Prajwal Yadav", "prajwal.yadav@arvind.com", "1234", 2, False),

        # ("Purv Nagar", "purv.nagar@bikaji.com", "1234", 3, True),
        # ("Nitin Sevak", "nitin.sevak@bikaji.com", "1234", 3, False),

    ]

    for name, email, password, org_id, is_admin in users_data:
        user = User(
            name=name,
            email=email,
            organization_id=org_id,
            is_active=True,
            is_admin=is_admin
        )
        user.set_password(password)
        db.session.add(user)

    db.session.commit()
    return "Users populated successfully!"


@populate_bp.route("/categories", methods=["GET"])
def populate_categories():
    categories_data = [
        # (name, organization_id)
        ("Finance Bots", 1),
        ("HR Bots", 1),
        ("IT Bots", 1),
        ("Sales Bots", 2),
        ("Marketing Bots", 2),
        ("Operations Bots", 3),
    ]

    for name, org_id in categories_data:
        category = BotCategory(
            name=name,
            organization_id=org_id
        )
        db.session.add(category)

    db.session.commit()
    return "Bot categories populated successfully!"


@populate_bp.route("/bots")
def populate_bots():
    try:

        # Sample Bot entries
        bots_data = [
            {
                "bot_name": "Invoice Processor",
                "description": "Automates invoice processing for finance team.",
                "organization_id": 1,
                "category_id": 1,
                "log_file_path": r"C:\Users\chirag.modi\Downloads\8.txt",
                "created_by": 1
            },
            {
                "bot_name": "Email Notifier",
                "description": "Sends automated notifications via email.",
                "organization_id": 1,
                "category_id": 2,
                "log_file_path": r"C:\Users\chirag.modi\Downloads\8.txt",
                "created_by": 1
            },
            {
                "bot_name": "Timesheet Processor",
                "description": "Collect Monthy Timesheet and Update into SAP system.",
                "organization_id": 1,
                "category_id": 2,
                "log_file_path": r"C:\Users\chirag.modi\Downloads\8.txt",
                "created_by": 1
            },
            {
                "bot_name": "Payroll Processor",
                "description": "Automates monthly payroll calculation and reporting.",
                "organization_id": 1,
                "category_id": 1,
                "log_file_path": r"C:\Users\chirag.modi\Downloads\8.txt",
                "created_by": 1
            },
            {
                "bot_name": "Inventory Updater",
                "description": "Updates inventory levels from warehouse to ERP system.",
                "organization_id": 1,
                "category_id": 1,
                "log_file_path": r"C:\Users\chirag.modi\Downloads\8.txt",
                "created_by": 1
            },
            {
                "bot_name": "Customer Feedback Collector",
                "description": "Aggregates customer feedback from multiple channels.",
                "organization_id": 2,
                "category_id": 4,
                "log_file_path": r"C:\Users\chirag.modi\Downloads\8.txt",
                "created_by": 1
            },
            {
                "bot_name": "Purchase Order Generator",
                "description": "Generates purchase orders automatically from requisitions.",
                "organization_id": 2,
                "category_id": 4,
                "log_file_path": r"C:\Users\chirag.modi\Downloads\8.txt",
                "created_by": 1
            },
            {
                "bot_name": "Report Scheduler",
                "description": "Schedules and emails reports to stakeholders.",
                "organization_id": 2,
                "category_id": 4,
                "log_file_path": r"C:\Users\chirag.modi\Downloads\8.txt",
                "created_by": 1
            },
            {
                "bot_name": "Lead Scraper",
                "description": "Scrapes potential leads from web and CRM sources.",
                "organization_id": 3,
                "category_id": 6,
                "log_file_path": r"C:\Users\chirag.modi\Downloads\8.txt",
                "created_by": 1
            },
            {
                "bot_name": "Expense Reconciliation",
                "description": "Matches employee expenses with receipts and records in ERP.",
                "organization_id": 3,
                "category_id": 6,
                "log_file_path": r"C:\Users\chirag.modi\Downloads\8.txt",
                "created_by": 1
            }
        ]

        for bot_data in bots_data:
            bot = Bot(**bot_data)
            db.session.add(bot)

        db.session.commit()
        return jsonify({"message": "Bots populated successfully!"})
    
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500
    


@populate_bp.route("/bot-assignments")
def populate_bot_assignments():
    try:
        # Optional: You can also assign multiple bots to multiple users
        assignments_data = [
            { "bot_id": 1, "user_id": 1, "assigned_by": 1 },
            { "bot_id": 2, "user_id": 2, "assigned_by": 1 },
            { "bot_id": 3, "user_id": 2, "assigned_by": 1 },
            { "bot_id": 4, "user_id": 2, "assigned_by": 1 },
            { "bot_id": 5, "user_id": 3, "assigned_by": 1 },
            { "bot_id": 6, "user_id": 4, "assigned_by": 1 },
            { "bot_id": 7, "user_id": 5, "assigned_by": 1 },
            { "bot_id": 8, "user_id": 5, "assigned_by": 1 },
            { "bot_id": 9, "user_id": 6, "assigned_by": 1 },
            { "bot_id": 10, "user_id": 7, "assigned_by": 1 },
        ]

        for data in assignments_data:
            assignment = BotAssignment(**data)
            db.session.add(assignment)

        db.session.commit()
        return jsonify({"message": "Bot assignments populated successfully!"})

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500
