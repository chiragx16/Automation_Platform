from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR, EVENT_JOB_MISSED
from threading import Lock
from datetime import datetime
from pathlib import Path
import subprocess, logging, atexit, os, pytz
from collections import defaultdict

from automation_platform.database.database import db
from automation_platform.database.models import Bot, BotSchedule, BotExecution, ExecutionStatus

logger = logging.getLogger(__name__)
ist = pytz.timezone("Asia/Kolkata")

# Global locks to prevent concurrent execution of same bot
bot_locks = {}
bot_locks_lock = Lock()  # Lock for the locks dictionary itself

# Thread-safe set for killed bots
killed_bots = set()
killed_bots_lock = Lock()

# Track running processes to allow kill/stop
running_processes = {}
running_processes_lock = Lock()

# Lock for log file writes
log_file_locks = defaultdict(Lock)


def _get_bot_lock(bot_id: int) -> Lock:
    """Thread-safe way to get or create a lock for a bot"""
    with bot_locks_lock:
        if bot_id not in bot_locks:
            bot_locks[bot_id] = Lock()
        return bot_locks[bot_id]


def _add_killed_bot(bot_id: int):
    """Thread-safe way to mark a bot as killed"""
    with killed_bots_lock:
        killed_bots.add(bot_id)


def _remove_killed_bot(bot_id: int):
    """Thread-safe way to remove a bot from killed set"""
    with killed_bots_lock:
        killed_bots.discard(bot_id)


def _is_bot_killed(bot_id: int) -> bool:
    """Thread-safe way to check if bot was killed"""
    with killed_bots_lock:
        return bot_id in killed_bots


def _add_running_process(bot_id: int, process):
    """Thread-safe way to track a running process"""
    with running_processes_lock:
        running_processes[bot_id] = process


def _remove_running_process(bot_id: int):
    """Thread-safe way to remove a running process"""
    with running_processes_lock:
        running_processes.pop(bot_id, None)


def _get_running_process(bot_id: int):
    """Thread-safe way to get a running process"""
    with running_processes_lock:
        return running_processes.get(bot_id)


# -------------------
# Module-level function for job execution
# -------------------
def _execute_bot_wrapper(bot_id: int, schedule_id: int = None, execution_id: int = None):
    """Module-level wrapper callable by APScheduler (safe for serialization)"""
    app = scheduler_service.app
    lock = _get_bot_lock(bot_id)
    execution = None

    # Try to acquire lock - skip if already running
    if not lock.acquire(blocking=False):
        logger.warning(f"Bot {bot_id} is already running. Skipping this execution.")
        return

    try:
        with app.app_context():
            # Validate bot BEFORE creating execution record
            bot = db.session.get(Bot, bot_id)
            if not bot:
                logger.error(f"Bot {bot_id} not found")
                return
            
            if not bot.is_active:
                logger.error(f"Bot {bot_id} is inactive")
                return

            # Create or get execution record
            if execution_id:
                execution = db.session.get(BotExecution, execution_id)
                if not execution:
                    logger.error(f"Execution {execution_id} not found")
                    return
            else:
                execution = BotExecution(
                    bot_id=bot_id,
                    schedule_id=schedule_id,
                    status=ExecutionStatus.PENDING,
                    scheduled_at=datetime.now(ist)
                )
                db.session.add(execution)
                db.session.commit()

            # Update to RUNNING
            execution.status = ExecutionStatus.RUNNING
            execution.started_at = datetime.now(ist)
            db.session.commit()
            logger.info(f"Starting execution {execution.execution_id} for bot {bot_id}")

            # Run the bot script
            result = _run_bot_script(bot, app)

            # Check if bot was killed manually (highest priority)
            if _is_bot_killed(bot_id):
                execution.status = ExecutionStatus.CANCELLED
                _remove_killed_bot(bot_id)
                execution.completed_at = datetime.now(ist)
                db.session.commit()
                logger.info(f"Execution {execution.execution_id} cancelled manually")
                return

            # Normal status handling
            if result['success']:
                execution.status = ExecutionStatus.SUCCESS
            elif result.get('timeout'):
                execution.status = ExecutionStatus.TIMEOUT
            else:
                execution.status = ExecutionStatus.FAILED

            execution.completed_at = datetime.now(ist)
            db.session.commit()
            logger.info(f"Execution {execution.execution_id} completed with status {execution.status.value}")

    except Exception as e:
        logger.error(f"Error executing bot {bot_id}: {e}", exc_info=True)
        
        # Update execution status on error
        if execution:
            try:
                with app.app_context():
                    # Refresh the execution object in this context
                    execution = db.session.get(BotExecution, execution.execution_id)
                    if execution:
                        # Check if killed during error handling
                        if _is_bot_killed(bot_id):
                            execution.status = ExecutionStatus.CANCELLED
                            _remove_killed_bot(bot_id)
                        else:
                            execution.status = ExecutionStatus.FAILED
                        
                        execution.completed_at = datetime.now(ist)
                        db.session.commit()
            except Exception as db_error:
                logger.error(f"Failed to update execution status: {db_error}", exc_info=True)
    
    finally:
        # Always release the lock
        lock.release()


# -------------------
# Bot script runner
# -------------------
def _run_bot_script(bot: Bot, app):
    """Execute the bot script and return results"""
    bot_id = bot.bot_id
    process = None
    
    try:
        if not bot.script_path:
            return {'success': False, 'error': "Bot script path not configured"}

        script_path = Path(bot.script_path).resolve()
        if not script_path.exists() or not script_path.is_file():
            return {'success': False, 'error': f"Script not found or invalid: {script_path}"}

        # Determine command based on file extension
        ext = script_path.suffix.lower()
        if ext == ".py":
            python_path = getattr(bot, 'venv_path', None)
            if python_path:
                python_executable = Path(python_path).resolve()
                if not python_executable.exists():
                    return {'success': False, 'error': f"Python executable not found: {python_executable}"}
                cmd = [str(python_executable), str(script_path)]
            else:
                cmd = ['python', str(script_path)]
        elif ext == ".exe":
            cmd = [str(script_path)]
        elif ext == ".sh":
            cmd = ['bash', str(script_path)]
        elif ext == ".bat":
            cmd = ['cmd', '/c', str(script_path)]
        else:
            if not os.access(script_path, os.X_OK):
                return {'success': False, 'error': f"Script is not executable: {script_path}"}
            cmd = [str(script_path)]

        # Start the process
        process = subprocess.Popen(
            cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE, 
            text=True, 
            cwd=script_path.parent
        )
        _add_running_process(bot_id, process)

        # Wait for completion with optional timeout
        timeout = getattr(app.config, 'BOT_EXECUTION_TIMEOUT', None)
        try:
            stdout, stderr = process.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            process.kill()
            process.communicate()  # Clean up
            _remove_running_process(bot_id)
            return {'success': False, 'timeout': True, 'error': "Execution timed out"}

        # Remove from running processes
        _remove_running_process(bot_id)

        # Write logs if configured
        if bot.log_file_path:
            _write_log(bot.log_file_path, stdout, stderr)

        return {
            'success': process.returncode == 0, 
            'timeout': False, 
            'output': stdout, 
            'error': stderr if process.returncode != 0 else None
        }

    except Exception as e:
        if process:
            try:
                process.kill()
            except:
                pass
        _remove_running_process(bot_id)
        logger.error(f"Error running bot {bot_id}: {e}", exc_info=True)
        return {'success': False, 'timeout': False, 'error': str(e)}


def kill_bot(bot_id: int):
    """
    Force-stop a running bot and update its execution status.
    Returns dict with success status and optional error message.
    """
    # Mark as killed FIRST (before any other operations)
    _add_killed_bot(bot_id)
    
    # Get the process
    process = _get_running_process(bot_id)
    if not process:
        _remove_killed_bot(bot_id)  # Clean up since bot wasn't running
        return {'success': False, 'error': "Bot not running"}
    
    try:
        # Update database BEFORE killing process to avoid race conditions
        with scheduler_service.app.app_context():
            execution = (
                db.session.query(BotExecution)
                .filter_by(bot_id=bot_id, status=ExecutionStatus.RUNNING)
                .order_by(BotExecution.started_at.desc())
                .first()
            )
            if execution:
                execution.status = ExecutionStatus.CANCELLED
                execution.completed_at = datetime.now(ist)
                db.session.commit()
                logger.info(f"Execution {execution.execution_id} marked as CANCELLED")

        # Now kill the process
        process.kill()
        process.wait(timeout=5)  # Wait for clean termination
        _remove_running_process(bot_id)
        logger.info(f"Bot {bot_id} killed successfully")

        return {'success': True}

    except subprocess.TimeoutExpired:
        logger.warning(f"Bot {bot_id} did not terminate gracefully, forcing...")
        _remove_running_process(bot_id)
        return {'success': True, 'warning': 'Process did not terminate gracefully'}
    
    except Exception as e:
        logger.error(f"Error killing bot {bot_id}: {e}", exc_info=True)
        _remove_killed_bot(bot_id)  # Clean up on failure
        return {'success': False, 'error': str(e)}


def _write_log(path: str, stdout: str, stderr: str):
    """Thread-safe log writing"""
    try:
        log_file = Path(path)
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Use a lock specific to this log file
        lock = log_file_locks[str(log_file)]
        
        with lock:
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(f"\n{'='*80}\nExecution at: {datetime.now(ist)}\n{'='*80}\n")
                if stdout: 
                    f.write(f"STDOUT:\n{stdout}\n")
                if stderr: 
                    f.write(f"STDERR:\n{stderr}\n")
    except Exception as e:
        logger.error(f"Error writing log to {path}: {e}", exc_info=True)


# -------------------
# Scheduler service
# -------------------
class BotSchedulerService:
    def __init__(self, app=None):
        self.scheduler = None
        self.app = app
        if app:
            self.init_app(app)

    def init_app(self, app):
        """Initialize the scheduler with Flask app"""
        self.app = app
        
        # Configure job store
        jobstores = {
            'default': SQLAlchemyJobStore(url=app.config['SQLALCHEMY_DATABASE_URI'])
        }
        
        # Configure executors - make thread pool size configurable
        thread_pool_size = app.config.get('SCHEDULER_THREAD_POOL_SIZE', 20)
        executors = {
            'default': ThreadPoolExecutor(thread_pool_size)
        }
        
        # Job defaults
        job_defaults = {
            'coalesce': True,  # Combine missed executions into one
            'max_instances': 1,  # Only one instance per job
            'misfire_grace_time': 300  # 5 minutes grace period
        }

        # Create and start scheduler
        self.scheduler = BackgroundScheduler(
            jobstores=jobstores, 
            executors=executors,
            job_defaults=job_defaults, 
            timezone=ist
        )
        
        # Add event listeners
        self.scheduler.add_listener(
            lambda e: logger.info(f"Job {e.job_id} executed"), 
            EVENT_JOB_EXECUTED
        )
        self.scheduler.add_listener(
            lambda e: logger.error(f"Job {e.job_id} failed: {e.exception}"), 
            EVENT_JOB_ERROR
        )
        self.scheduler.add_listener(
            lambda e: logger.warning(f"Job {e.job_id} missed"), 
            EVENT_JOB_MISSED
        )
        
        self.scheduler.start()
        atexit.register(lambda: self.scheduler.shutdown())
        logger.info("APScheduler started successfully")

    def add_schedule(self, schedule: BotSchedule):
        """Add or update a schedule in the scheduler"""
        if not schedule.is_active:
            self.remove_schedule(schedule.schedule_id)
            return
        
        job_id = f"schedule_{schedule.schedule_id}"
        
        try:
            # Validate cron expression
            trigger = CronTrigger.from_crontab(schedule.cron_expression, timezone=ist)
            
            # Add job
            self.scheduler.add_job(
                _execute_bot_wrapper, 
                trigger=trigger,
                args=[schedule.bot_id, schedule.schedule_id, None],
                id=job_id,
                name=f"{schedule.name} (Bot: {schedule.bot.bot_name})",
                replace_existing=True
            )
            logger.info(f"Schedule {schedule.schedule_id} added/updated for bot {schedule.bot_id}")
            
        except ValueError as e:
            logger.error(f"Invalid cron expression for schedule {schedule.schedule_id}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error adding schedule {schedule.schedule_id}: {e}", exc_info=True)
            raise

    def remove_schedule(self, schedule_id: int):
        """Remove a schedule from the scheduler"""
        job_id = f"schedule_{schedule_id}"
        try:
            if self.scheduler.get_job(job_id):
                self.scheduler.remove_job(job_id)
                logger.info(f"Schedule {schedule_id} removed")
        except Exception as e:
            logger.error(f"Error removing schedule {schedule_id}: {e}", exc_info=True)

    def pause_schedule(self, schedule_id: int):
        """Pause a schedule"""
        job_id = f"schedule_{schedule_id}"
        try:
            job = self.scheduler.get_job(job_id)
            if job:
                job.pause()
                logger.info(f"Schedule {schedule_id} paused")
            else:
                logger.warning(f"Schedule {schedule_id} not found")
        except Exception as e:
            logger.error(f"Error pausing schedule {schedule_id}: {e}", exc_info=True)

    def resume_schedule(self, schedule_id: int):
        """Resume a paused schedule"""
        job_id = f"schedule_{schedule_id}"
        try:
            job = self.scheduler.get_job(job_id)
            if job:
                job.resume()
                logger.info(f"Schedule {schedule_id} resumed")
            else:
                logger.warning(f"Schedule {schedule_id} not found")
        except Exception as e:
            logger.error(f"Error resuming schedule {schedule_id}: {e}", exc_info=True)

    def run_bot_immediately(self, bot_id: int, user_id: int):
        """Schedule a bot to run immediately"""
        with self.app.app_context():
            # Validate bot exists and is active
            bot = db.session.get(Bot, bot_id)
            if not bot:
                raise ValueError(f"Bot {bot_id} not found")
            if not bot.is_active:
                raise ValueError(f"Bot {bot_id} is inactive")
            
            # Create execution record
            execution = BotExecution(
                bot_id=bot_id, 
                triggered_by_user_id=user_id,
                status=ExecutionStatus.PENDING,
                scheduled_at=datetime.now(ist)
            )
            db.session.add(execution)
            db.session.commit()
            
            # Schedule immediate execution
            job_id = f"immediate_{execution.execution_id}"
            self.scheduler.add_job(
                _execute_bot_wrapper,
                args=[bot_id, None, execution.execution_id],
                id=job_id,
                name=f"Immediate execution - Bot {bot_id}",
                replace_existing=True
            )
            logger.info(f"Bot {bot_id} scheduled for immediate execution by user {user_id}")
            
            return execution

    def get_all_jobs(self):
        """Get information about all scheduled jobs"""
        try:
            jobs = []
            for job in self.scheduler.get_jobs():
                jobs.append({
                    'id': job.id,
                    'name': job.name,
                    'next_run': job.next_run_time.isoformat() if job.next_run_time else None,
                    'trigger': str(job.trigger)
                })
            return jobs
        except Exception as e:
            logger.error(f"Error getting jobs: {e}", exc_info=True)
            return []
    
    def get_running_bots(self):
        """
        Returns a list of bot_ids that are currently running.
        """
        with running_processes_lock:
            return list(running_processes.keys())
    
    def cleanup_completed_immediate_jobs(self):
        """
        Remove completed immediate execution jobs from the job store.
        Call this periodically (e.g., daily) to prevent job store bloat.
        """
        try:
            removed_count = 0
            for job in self.scheduler.get_jobs():
                if job.id.startswith('immediate_') and job.next_run_time is None:
                    self.scheduler.remove_job(job.id)
                    removed_count += 1
            
            if removed_count > 0:
                logger.info(f"Cleaned up {removed_count} completed immediate jobs")
        except Exception as e:
            logger.error(f"Error cleaning up jobs: {e}", exc_info=True)


# -------------------
# Global scheduler instance
# -------------------
scheduler_service = BotSchedulerService()