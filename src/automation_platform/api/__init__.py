from flask import Blueprint

from .home import home_api
from .bot_control import bot_control_api
from .launchpad import launchpad_api
from .bot_routes import bot_api
from .populate import populate_bp
from .schedule import schedule_api
from .reports import reports_api

api = Blueprint('api', __name__)

# api.register_blueprint(bot_api, url_prefix='/api/bots')
api.register_blueprint(home_api, url_prefix='/api/home')
api.register_blueprint(bot_control_api, url_prefix='/api/botcontrol')
api.register_blueprint(launchpad_api, url_prefix='/api/launchpad')
api.register_blueprint(populate_bp, url_prefix='/api/populate')
api.register_blueprint(schedule_api, url_prefix='/api/schedule')
api.register_blueprint(reports_api, url_prefix='/api/reports')







