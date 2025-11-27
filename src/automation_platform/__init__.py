"""
app.py - Flask application with APScheduler integration
"""

from flask import Flask, session, redirect, url_for, jsonify
from flask_cors import CORS
from automation_platform.settings import settings
from automation_platform.database.database import init_db
from automation_platform.auth.routes import auth_bp
from automation_platform.api import api
from datetime import timedelta
from automation_platform.scheduler.scheduler import scheduler_service
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def create_app():
    app = Flask(
        __name__,
        template_folder="templates",  
        static_folder="static",
    )

    # --- Configurations ---
    app.secret_key = settings.SECRET_KEY
    app.permanent_session_lifetime = timedelta(days=30)
    app.config["SQLALCHEMY_DATABASE_URI"] = settings.SQLALCHEMY_DATABASE_URI
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["BOT_EXECUTION_TIMEOUT"] = None

    # --- Extensions init ---
    CORS(app)
    init_db(app)
    
    # Initialize scheduler
    scheduler_service.init_app(app)
    
    # --- Register Blueprints ---
    app.register_blueprint(api)
    app.register_blueprint(auth_bp)

    # Register global routes
    register_routes(app)

    return app


def register_routes(app):
    """Register application-level routes"""
    from automation_platform.database.models import Organization
    from automation_platform.database.database import db
    
    @app.route("/")
    def index():
        if "user" not in session:
            return redirect(url_for("auth.login_page"))
        return redirect(url_for("api.home_bp.home"))
    
    @app.route("/login_orgs")
    def login_orgs():
        # Query active organizations
        orgs = db.session.query(Organization).filter_by(is_active=True).all()
        
        organizations = [
            {
                "organization_id": org.organization_id,
                "organization_name": org.organization_name
            }
            for org in orgs
        ]
        
        return jsonify(organizations)