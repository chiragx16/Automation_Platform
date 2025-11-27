from sqlalchemy import (
    Column, Integer, String, Boolean, Text, TIMESTAMP,
    ForeignKey, Enum, text
)
from sqlalchemy.orm import relationship
from automation_platform.database.database import db
import enum
from werkzeug.security import generate_password_hash, check_password_hash


# ===========================
# ENUM for Execution Status
# ===========================
class ExecutionStatus(enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    TIMEOUT = "TIMEOUT"


# ===========================
# Organization
# ===========================
class Organization(db.Model):
    __tablename__ = "Organization"

    organization_id = Column(Integer, primary_key=True, autoincrement=True)
    organization_name = Column(String(255), unique=True, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"))

    users = relationship("User", back_populates="organization", cascade="all, delete")
    categories = relationship("BotCategory", back_populates="organization", cascade="all, delete")
    bots = relationship("Bot", back_populates="organization", cascade="all, delete")


# ===========================
# User
# ===========================
class User(db.Model):
    __tablename__ = "User"

    user_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False)
    password_hash = Column(String(255), nullable=False)

    organization_id = Column(Integer, ForeignKey("Organization.organization_id", ondelete="CASCADE"), nullable=False)

    is_active = Column(Boolean, default=True, nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)
    created_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"))

    organization = relationship("Organization", back_populates="users")

    bots_created = relationship("Bot", back_populates="creator")

    assignments = relationship(
        "BotAssignment",
        foreign_keys="BotAssignment.user_id",
        back_populates="user",
        cascade="all, delete"
    )

    assigned_tasks = relationship(
        "BotAssignment",
        foreign_keys="BotAssignment.assigned_by",
        back_populates="assigned_by_user"
    )

    executions_triggered = relationship(
        "BotExecution",
        foreign_keys="BotExecution.triggered_by_user_id",
        back_populates="triggered_by_user"
    )

    def set_password(self, plain_password: str):
        self.password_hash = generate_password_hash(plain_password)

    def verify_password(self, plain_password: str):
        return check_password_hash(self.password_hash, plain_password)


# ===========================
# Bot Category
# ===========================
class BotCategory(db.Model):
    __tablename__ = "BotCategory"

    category_id = Column(Integer, primary_key=True, autoincrement=True)
    organization_id = Column(Integer, ForeignKey("Organization.organization_id", ondelete="CASCADE"), nullable=False)

    name = Column(String(100), nullable=False)

    organization = relationship("Organization", back_populates="categories")
    bots = relationship("Bot", back_populates="category", cascade="all, delete")


# ===========================
# Bot
# ===========================
class Bot(db.Model):
    __tablename__ = "Bot"

    bot_id = Column(Integer, primary_key=True, autoincrement=True)
    bot_name = Column(String(255), nullable=False)
    description = Column(Text)

    organization_id = Column(Integer, ForeignKey("Organization.organization_id", ondelete="CASCADE"), nullable=False)
    category_id = Column(Integer, ForeignKey("BotCategory.category_id", ondelete="SET NULL"), nullable=True)

    is_active = Column(Boolean, default=True, nullable=False)

    # Absolute path to bot script/executable
    script_path = Column(Text, nullable=False)

    # Path to bot’s virtual environment
    venv_path = Column(Text, nullable=False)   

    # Path to log file
    log_file_path = Column(Text, nullable=True)

    # Bot custom URL
    bot_custom_url = Column(Text, nullable=True)

    created_by = Column(Integer, ForeignKey("User.user_id"), nullable=False)

    created_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"), server_onupdate=text("CURRENT_TIMESTAMP"))

    organization = relationship("Organization", back_populates="bots")
    category = relationship("BotCategory", back_populates="bots")
    creator = relationship("User", back_populates="bots_created")

    assignments = relationship("BotAssignment", back_populates="bot", cascade="all, delete")
    schedules = relationship("BotSchedule", back_populates="bot", cascade="all, delete")
    executions = relationship("BotExecution", back_populates="bot", passive_deletes=True)


# ===========================
# Bot Assignment
# ===========================
class BotAssignment(db.Model):
    __tablename__ = "BotAssignment"

    id = Column(Integer, primary_key=True, autoincrement=True)
    bot_id = Column(Integer, ForeignKey("Bot.bot_id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("User.user_id", ondelete="CASCADE"), nullable=False)

    assigned_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"))
    assigned_by = Column(Integer, ForeignKey("User.user_id"), nullable=False)

    bot = relationship("Bot", back_populates="assignments")

    user = relationship(
        "User",
        foreign_keys=[user_id],
        back_populates="assignments"
    )

    assigned_by_user = relationship(
        "User",
        foreign_keys=[assigned_by],
        back_populates="assigned_tasks"
    )


# ===========================
# Bot Schedule
# ===========================
class BotSchedule(db.Model):
    __tablename__ = "BotSchedule"

    schedule_id = Column(Integer, primary_key=True, autoincrement=True)
    bot_id = Column(Integer, ForeignKey("Bot.bot_id", ondelete="CASCADE"), nullable=False)

    name = Column(String(255), nullable=False)
    cron_expression = Column(String(100), nullable=False)
    timezone = Column(String(50), nullable=False, default="UTC")

    is_active = Column(Boolean, default=True, nullable=False)
    created_by = Column(Integer, ForeignKey("User.user_id"), nullable=False)

    created_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"))

    bot = relationship("Bot", back_populates="schedules")
    creator = relationship("User")
    executions = relationship("BotExecution", back_populates="schedule", passive_deletes=True)


# ===========================
# Bot Execution
# ===========================
class BotExecution(db.Model):
    __tablename__ = "BotExecution"

    execution_id = Column(Integer, primary_key=True, autoincrement=True)

    bot_id = Column(Integer, ForeignKey("Bot.bot_id", ondelete="SET NULL"), nullable=True)
    schedule_id = Column(Integer, ForeignKey("BotSchedule.schedule_id", ondelete="SET NULL"), nullable=True)
    triggered_by_user_id = Column(Integer, ForeignKey("User.user_id", ondelete="SET NULL"))

    status = Column(Enum(ExecutionStatus), default=ExecutionStatus.PENDING, nullable=False)

    scheduled_at = Column(TIMESTAMP, nullable=True)
    started_at = Column(TIMESTAMP, nullable=True)
    completed_at = Column(TIMESTAMP, nullable=True)

    created_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"))

    bot = relationship("Bot", back_populates="executions")
    schedule = relationship("BotSchedule", back_populates="executions")
    triggered_by_user = relationship("User", back_populates="executions_triggered")


# ===========================
# Bot Custome Log Table
# ===========================
class BotLogSource(db.Model):
    __tablename__ = "BotLogSource"

    id = Column(Integer, primary_key=True, autoincrement=True)
    bot_id = Column(Integer, ForeignKey("Bot.bot_id", ondelete="CASCADE"), nullable=False)

    # Friendly name to display on UI
    display_name = Column(String(255), nullable=False)

    # Route inside the bot that returns logs
    endpoint_path = Column(String(255), nullable=False)
    
    bot = relationship("Bot", backref="log_sources", cascade="all, delete")
