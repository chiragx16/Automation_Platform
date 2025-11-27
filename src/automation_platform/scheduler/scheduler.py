"""
src/automation_platform/scheduler/scheduler.py
APScheduler service for bot execution management
"""

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR, EVENT_JOB_MISSED
import logging, os
import atexit
from datetime import datetime
from threading import Lock
import subprocess
from pathlib import Path
import pytz

from automation_platform.database.database import db
from automation_platform.database.models import (
    BotSchedule, BotExecution, Bot, ExecutionStatus
)

logger = logging.getLogger(__name__)

# Global locks to prevent concurrent execution of same bot
bot_locks = {}


ist = pytz.timezone("Asia/Kolkata")


def _run_bot_script(bot: Bot, app):
    """
    Execute the actual bot script/executable from any system path
    
    Args:
        bot: Bot model instance (must have script_path attribute)
        app: Flask app instance for config access
        
    Returns:
        dict with 'success', 'timeout', 'output', 'error'
    """
    try:
        # Get script path from bot model
        if not hasattr(bot, 'script_path') or not bot.script_path:
            logger.error(f"Bot {bot.bot_id} has no script_path defined")
            return {
                'success': False,
                'error': "Bot script path not configured"
            }
        
        # Convert to Path object and validate
        script_path = Path(bot.script_path)
        
        # Security: Ensure path is absolute or resolve it
        if not script_path.is_absolute():
            logger.warning(f"Relative path provided for bot {bot.bot_id}, resolving to absolute")
            script_path = script_path.resolve()
        
        # Validate script exists
        if not script_path.exists():
            logger.error(f"Bot script not found: {script_path}")
            return {
                'success': False,
                'error': f"Script not found: {script_path}"
            }
        
        # Validate it's a file (not directory)
        if not script_path.is_file():
            logger.error(f"Bot script path is not a file: {script_path}")
            return {
                'success': False,
                'error': f"Path is not a file: {script_path}"
            }
        
        # Check file permissions (readable and executable for non-Python files)
        if not os.access(script_path, os.R_OK):
            logger.error(f"Bot script is not readable: {script_path}")
            return {
                'success': False,
                'error': f"Script is not readable: {script_path}"
            }
        
        abs_path = script_path.resolve()
        
        # Determine command based on file extension
        file_ext = abs_path.suffix.lower()
        
        if file_ext == '.py':
            # Check if bot has a specific Python interpreter
            if hasattr(bot, 'venv_path') and bot.venv_path:
                python_path = Path(bot.venv_path)
                if python_path.exists() and python_path.is_file():
                    cmd = [str(python_path), str(abs_path)]
                    logger.info(f"Using custom Python interpreter: {python_path}")
                else:
                    logger.warning(f"Custom Python interpreter not found: {python_path}, using default")
                    cmd = ['python', str(abs_path)]
            else:
                # Use default python
                cmd = ['python', str(abs_path)]
        elif file_ext == '.exe':
            # Windows executable
            cmd = [str(abs_path)]
        elif file_ext == '.sh':
            # Shell script (Unix/Linux)
            cmd = ['bash', str(abs_path)]
        elif file_ext == '.bat':
            # Batch script (Windows)
            cmd = ['cmd', '/c', str(abs_path)]
        else:
            # Try to execute directly (must have executable permission)
            if not os.access(abs_path, os.X_OK):
                logger.error(f"Bot script is not executable: {abs_path}")
                return {
                    'success': False,
                    'error': f"Script is not executable: {abs_path}"
                }
            cmd = [str(abs_path)]
        
        logger.info(f"Executing bot {bot.bot_id} with command: {' '.join(cmd)}")
        
        # Get timeout from config or use default
        timeout = getattr(app.config, 'BOT_EXECUTION_TIMEOUT', None)

        # Common arguments
        subprocess_kwargs = {
            'capture_output': True,
            'text': True,
            'check': False,
            'cwd': abs_path.parent
        }

        # Execute with or without timeout
        if timeout:
            result = subprocess.run(cmd, timeout=timeout, **subprocess_kwargs)
        else:
            result = subprocess.run(cmd, **subprocess_kwargs)

        
        # Log output to bot's log file if specified
        if bot.log_file_path:
            _write_log(bot.log_file_path, result.stdout, result.stderr)
        
        return {
            'success': result.returncode == 0,
            'timeout': False,
            'output': result.stdout,
            'error': result.stderr if result.returncode != 0 else None
        }
        
    except subprocess.TimeoutExpired:
        logger.error(f"Bot {bot.bot_id} execution timed out")
        return {
            'success': False,
            'timeout': True,
            'error': 'Execution timed out'
        }
    except Exception as e:
        logger.error(f"Error running bot {bot.bot_id}: {str(e)}")
        return {
            'success': False,
            'timeout': False,
            'error': str(e)
        }


def _write_log(log_path: str, stdout: str, stderr: str):
    """Write execution logs to file"""
    try:
        log_file = Path(log_path)
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(log_file, 'a') as f:
            f.write(f"\n{'='*80}\n")
            f.write(f"Execution at: {datetime.now(ist)}\n")
            f.write(f"{'='*80}\n")
            if stdout:
                f.write(f"STDOUT:\n{stdout}\n")
            if stderr:
                f.write(f"STDERR:\n{stderr}\n")
    except Exception as e:
        logger.error(f"Error writing log file: {str(e)}")


class BotSchedulerService:
    """Service to manage bot scheduling and execution"""
    
    def __init__(self, app=None):
        self.scheduler = None
        self.app = app
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize scheduler with Flask app"""
        self.app = app
        
        # Configure job stores
        jobstores = {
            'default': SQLAlchemyJobStore(
                url=app.config['SQLALCHEMY_DATABASE_URI']
            )
        }
        
        # Configure executors
        executors = {
            'default': ThreadPoolExecutor(20)
        }
        
        # Job defaults to prevent overlap
        job_defaults = {
            'coalesce': True,  # Combine missed runs
            'max_instances': 1,  # Only one instance per job
            'misfire_grace_time': 300  # 5 minutes grace period
        }

        
        
        # Create scheduler
        self.scheduler = BackgroundScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
            daemon=True,
            timezone=ist
        )
        
        # Add event listeners
        self.scheduler.add_listener(
            self._job_executed_listener,
            EVENT_JOB_EXECUTED
        )
        self.scheduler.add_listener(
            self._job_error_listener,
            EVENT_JOB_ERROR
        )
        self.scheduler.add_listener(
            self._job_missed_listener,
            EVENT_JOB_MISSED
        )
        
        # Start scheduler
        self.scheduler.start()
        logger.info("APScheduler started successfully")
        
        # Register shutdown
        atexit.register(lambda: self.scheduler.shutdown())
    
    def _job_executed_listener(self, event):
        """Handle successful job execution"""
        logger.info(f"Job {event.job_id} executed successfully")
    
    def _job_error_listener(self, event):
        """Handle job execution errors"""
        logger.error(f"Job {event.job_id} failed: {event.exception}")
    
    def _job_missed_listener(self, event):
        """Handle missed job executions"""
        logger.warning(f"Job {event.job_id} missed scheduled run")
    
    def add_schedule(self, schedule: BotSchedule):
        """
        Add or update a bot schedule in APScheduler
        
        Args:
            schedule: BotSchedule model instance
        """
        if not schedule.is_active:
            self.remove_schedule(schedule.schedule_id)
            return
        
        job_id = f"schedule_{schedule.schedule_id}"
        
        try:

            # Create cron trigger
            trigger = CronTrigger.from_crontab(
                schedule.cron_expression,
                timezone=ist
            )
            
            # Add or replace job
            self.scheduler.add_job(
                func=_execute_bot_wrapper,
                trigger=trigger,
                args=[schedule.bot_id, schedule.schedule_id, None],
                id=job_id,
                name=f"{schedule.name} (Bot: {schedule.bot.bot_name})",
                replace_existing=True
            )
            
            logger.info(f"Schedule {schedule.schedule_id} added/updated for bot {schedule.bot_id}")
            
        except Exception as e:
            logger.error(f"Error adding schedule {schedule.schedule_id}: {str(e)}")
            raise
    
    def remove_schedule(self, schedule_id: int):
        """Remove a schedule from APScheduler"""
        job_id = f"schedule_{schedule_id}"
        
        try:
            if self.scheduler.get_job(job_id):
                self.scheduler.remove_job(job_id)
                logger.info(f"Schedule {schedule_id} removed")
        except Exception as e:
            logger.error(f"Error removing schedule {schedule_id}: {str(e)}")
    
    def run_bot_immediately(self, bot_id: int, user_id: int):
        """
        Execute a bot immediately (outside of schedule)
        
        Args:
            bot_id: Bot ID to execute
            user_id: User triggering the execution
            
        Returns:
            BotExecution instance
        """
        with self.app.app_context():
            # Create execution record
            execution = BotExecution(
                bot_id=bot_id,
                triggered_by_user_id=user_id,
                status=ExecutionStatus.PENDING,
                scheduled_at=datetime.now(ist)
            )
            db.session.add(execution)
            db.session.commit()
            
            execution_id = execution.execution_id
            
            # Schedule immediate execution
            job_id = f"immediate_{execution_id}"
            
            self.scheduler.add_job(
                func=_execute_bot_wrapper,
                args=[bot_id, None, execution_id],
                id=job_id,
                name=f"Immediate execution - Bot {bot_id}",
                replace_existing=True
            )
            
            logger.info(f"Bot {bot_id} scheduled for immediate execution by user {user_id}")
            
            return execution
    
    def load_schedules_from_db(self):
        """Load all active schedules from database on startup"""
        with self.app.app_context():
            schedules = BotSchedule.query.filter_by(is_active=True).all()
            
            for schedule in schedules:
                try:
                    self.add_schedule(schedule)
                except Exception as e:
                    logger.error(f"Error loading schedule {schedule.schedule_id}: {str(e)}")
            
            logger.info(f"Loaded {len(schedules)} active schedules from database")
    
    def get_all_jobs(self):
        """Get list of all scheduled jobs"""
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                'id': job.id,
                'name': job.name,
                'next_run': job.next_run_time.isoformat() if job.next_run_time else None,
                'trigger': str(job.trigger)
            })
        return jobs
    
    def pause_schedule(self, schedule_id: int):
        """Pause a schedule without removing it"""
        job_id = f"schedule_{schedule_id}"
        try:
            job = self.scheduler.get_job(job_id)
            if job:
                job.pause()
                logger.info(f"Schedule {schedule_id} paused")
        except Exception as e:
            logger.error(f"Error pausing schedule {schedule_id}: {str(e)}")
    
    def resume_schedule(self, schedule_id: int):
        """Resume a paused schedule"""
        job_id = f"schedule_{schedule_id}"
        try:
            job = self.scheduler.get_job(job_id)
            if job:
                job.resume()
                logger.info(f"Schedule {schedule_id} resumed")
        except Exception as e:
            logger.error(f"Error resuming schedule {schedule_id}: {str(e)}")


# Global scheduler instance
scheduler_service = BotSchedulerService()


def _execute_bot_wrapper(bot_id: int, schedule_id: int = None, execution_id: int = None):
    """Wrapper to call _execute_bot with app context"""

    app = scheduler_service.app
    
    # Get or create lock for this bot
    if bot_id not in bot_locks:
        bot_locks[bot_id] = Lock()
    
    lock = bot_locks[bot_id]
    
    # Try to acquire lock
    if not lock.acquire(blocking=False):
        logger.warning(f"Bot {bot_id} is already running. Skipping this execution.")
        return
    
    try:
        with app.app_context():
            # Get bot details
            bot = db.session.get(Bot, bot_id)
            if not bot or not bot.is_active:
                logger.error(f"Bot {bot_id} not found or inactive")
                return
            
            

            # Create or get execution record
            if execution_id:
                execution = db.session.get(BotExecution, execution_id)
            else:
                execution = BotExecution(
                    bot_id=bot_id,
                    schedule_id=schedule_id,
                    status=ExecutionStatus.PENDING,
                    scheduled_at=datetime.now(ist)
                )
                db.session.add(execution)
                db.session.commit()
            
            # Update status to RUNNING
            execution.status = ExecutionStatus.RUNNING
            execution.started_at = datetime.now(ist)
            db.session.commit()
            
            logger.info(f"Starting execution {execution.execution_id} for bot {bot_id}")
            
            # Execute the bot script
            result = _run_bot_script(bot, app)
            
            # Update execution status based on result
            if result['success']:
                execution.status = ExecutionStatus.SUCCESS
            elif result.get('timeout'):
                execution.status = ExecutionStatus.TIMEOUT
            else:
                execution.status = ExecutionStatus.FAILED
            
            execution.completed_at = datetime.now(ist)
            db.session.commit()
            
            logger.info(
                f"Execution {execution.execution_id} completed with status {execution.status.value}"
            )
            
    except Exception as e:
        logger.error(f"Error executing bot {bot_id}: {str(e)}")
        
        # Update execution status to FAILED
        try:
            with app.app_context():
                if execution_id:
                    execution = db.session.get(BotExecution, execution_id)
                    if execution:
                        execution.status = ExecutionStatus.FAILED
                        execution.completed_at = datetime.now(ist)
                        db.session.commit()
        except:
            pass
    
    finally:
        # Always release the lock
        lock.release()