from flask import Blueprint

from .home import home_bp
from .bot_control import bot_control_bp
from .launchpad import launchpad_bp

from .populate import populate_bp
from .schedule import schedule_bp
from .schedule_reports import schedule_reports_bp
from .bot_reports import bot_reports_bp

api = Blueprint('api', __name__)

api.register_blueprint(home_bp, url_prefix='/api/home')
api.register_blueprint(bot_control_bp, url_prefix='/api/botcontrol')
api.register_blueprint(launchpad_bp, url_prefix='/api/launchpad')
api.register_blueprint(populate_bp, url_prefix='/api/populate')
api.register_blueprint(schedule_bp, url_prefix='/api/schedule')
api.register_blueprint(schedule_reports_bp, url_prefix='/api/schedule_reports')
api.register_blueprint(bot_reports_bp, url_prefix='/api/bot_reports')







