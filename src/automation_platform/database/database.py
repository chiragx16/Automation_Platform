# database.py
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

def init_db(app):
    """Initialize database with app."""
    db.init_app(app)
    
    with app.app_context():
        # Import all models here to register them
        from automation_platform.database import models  # noqa
        db.create_all()
    
    return db