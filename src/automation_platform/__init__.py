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
from logging.handlers import RotatingFileHandler
import os

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
    app.config["SCHEDULER_THREAD_POOL_SIZE"] = 20

    # --- Setup Logging ---
    setup_logging(app)

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


def setup_logging(app):
    """Configure separate logging for Flask app and scheduler"""
    
    # Create logs directory
    os.makedirs('logs', exist_ok=True)
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    simple_formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # ============================================
    # 1. Flask App Logger (app.log)
    # ============================================
    app_handler = RotatingFileHandler(
        'logs/app.log',
        maxBytes=10485760,  # 10MB
        backupCount=5
    )
    app_handler.setFormatter(simple_formatter)
    app_handler.setLevel(logging.INFO)
    
    # Configure Flask's logger
    app.logger.addHandler(app_handler)
    app.logger.setLevel(logging.INFO)
    
    # ============================================
    # 2. Scheduler Logger (scheduler.log)
    # ============================================
    scheduler_handler = RotatingFileHandler(
        'logs/scheduler.log',
        maxBytes=10485760,  # 10MB
        backupCount=10
    )
    scheduler_handler.setFormatter(detailed_formatter)
    scheduler_handler.setLevel(logging.INFO)
    
    # Get scheduler logger
    scheduler_logger = logging.getLogger('automation_platform.scheduler')
    scheduler_logger.addHandler(scheduler_handler)
    scheduler_logger.setLevel(logging.INFO)
    scheduler_logger.propagate = False  # Don't propagate to root logger
    
    # ============================================
    # 3. APScheduler Logger (scheduler.log - same file)
    # ============================================
    apscheduler_logger = logging.getLogger('apscheduler')
    apscheduler_logger.addHandler(scheduler_handler)
    apscheduler_logger.setLevel(logging.INFO)
    apscheduler_logger.propagate = False
    
    # ============================================
    # 4. Error Logger (errors.log - all errors)
    # ============================================
    error_handler = RotatingFileHandler(
        'logs/errors.log',
        maxBytes=10485760,  # 10MB
        backupCount=5
    )
    error_handler.setFormatter(detailed_formatter)
    error_handler.setLevel(logging.ERROR)
    
    # Add error handler to both app and scheduler
    app.logger.addHandler(error_handler)
    scheduler_logger.addHandler(error_handler)
    
    # ============================================
    # 5. Console Output (Optional)
    # ============================================
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(simple_formatter)
    console_handler.setLevel(logging.INFO)
    
    app.logger.addHandler(console_handler)
    scheduler_logger.addHandler(console_handler)
    
    app.logger.info("Logging configured successfully")


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