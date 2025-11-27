from flask import Blueprint, session, request, jsonify
from automation_platform.database.database import db
from automation_platform.database.models import (
    Bot, BotSchedule, BotExecution, ExecutionStatus, User
)
from automation_platform.scheduler.scheduler import scheduler_service
from automation_platform.auth.middleware import login_required
from datetime import datetime, timezone
from croniter import croniter
import pytz

schedule_bp = Blueprint('schedule_bp', __name__)

@schedule_bp.route('/run/<int:bot_id>', methods=['POST'])
@login_required
def run_bot_immediately(bot_id):
    """
    Run a bot immediately (outside of schedule)
    """
    try:
        # user_id = request.user_id  # From auth middleware
        user_id = session.get("user", {}).get("id")
        
        # Check if bot exists and user has access
        bot = db.session.get(Bot, bot_id)
        if not bot:
            return jsonify({'error': 'Bot not found'}), 404
        
        if not bot.is_active:
            return jsonify({'error': 'Bot is inactive'}), 400
        
        # Check user permissions (implement your logic)
        # For now, just check if user belongs to same organization
        user = db.session.get(User, user_id)
        if user.is_admin:
            pass
        else:
            if user.organization_id != bot.organization_id:
                return jsonify({'error': 'Unauthorized'}), 403
        
        # Execute bot immediately
        execution = scheduler_service.run_bot_immediately(bot_id, user_id)
        
        return jsonify({
            'success': True,
            'message': 'Bot execution started',
            'execution_id': execution.execution_id,
            'status': execution.status.value
        }), 202
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@schedule_bp.route('/schedule_bot', methods=['POST'])
@login_required
def create_schedule():
    """
    Create a new bot schedule
    
    Body:
    {
        "bot_id": 1,
        "name": "Daily Report",
        "cron_expression": "0 9 * * *",
        "timezone": "America/New_York",
        "is_active": true
    }
    """
    try:
        data = request.get_json()
        user_id = session.get("user", {}).get("id")
        
        # Validate required fields
        required = ['bot_id', 'name', 'cron_expression']
        if not all(field in data for field in required):
            return jsonify({'error': 'Missing required fields'}), 400
        
        # Validate bot exists
        bot = db.session.get(Bot, data['bot_id'])
        if not bot:
            return jsonify({'error': 'Bot not found'}), 404
        
        # Check permissions
        user = db.session.get(User, user_id)
        if user.organization_id != bot.organization_id:
            return jsonify({'error': 'Unauthorized'}), 403
        
        # Validate cron expression
        try:
            croniter(data['cron_expression'])
        except Exception:
            return jsonify({'error': 'Invalid cron expression'}), 400
        
        # Validate timezone
        timezone = data.get('timezone', 'UTC')
        try:
            pytz.timezone(timezone)
        except Exception:
            return jsonify({'error': 'Invalid timezone'}), 400
        
        # Create schedule
        schedule = BotSchedule(
            bot_id=data['bot_id'],
            name=data['name'],
            cron_expression=data['cron_expression'],
            timezone=timezone,
            is_active=data.get('is_active', True),
            created_by=user_id
        )
        
        db.session.add(schedule)
        db.session.commit()
        
        # Add to APScheduler
        if schedule.is_active:
            scheduler_service.add_schedule(schedule)
        
        return jsonify({
            'success': True,
            'schedule_id': schedule.schedule_id,
            'message': 'Schedule created successfully'
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@schedule_bp.route('/schedule_bot/<int:schedule_id>', methods=['PUT'])
@login_required
def update_schedule(schedule_id):
    """
    Update an existing schedule
    """
    try:
        data = request.get_json()
        user_id = request.user_id
        
        schedule = db.session.get(BotSchedule, schedule_id)
        if not schedule:
            return jsonify({'error': 'Schedule not found'}), 404
        
        # Check permissions
        user = db.session.get(User, user_id)
        if user.organization_id != schedule.bot.organization_id:
            return jsonify({'error': 'Unauthorized'}), 403
        
        # Update fields
        if 'name' in data:
            schedule.name = data['name']
        
        if 'cron_expression' in data:
            # Validate cron
            try:
                croniter(data['cron_expression'])
                schedule.cron_expression = data['cron_expression']
            except Exception:
                return jsonify({'error': 'Invalid cron expression'}), 400
        
        if 'timezone' in data:
            try:
                pytz.timezone(data['timezone'])
                schedule.timezone = data['timezone']
            except Exception:
                return jsonify({'error': 'Invalid timezone'}), 400
        
        if 'is_active' in data:
            schedule.is_active = data['is_active']
        
        db.session.commit()
        
        # Update APScheduler
        if schedule.is_active:
            scheduler_service.add_schedule(schedule)
        else:
            scheduler_service.remove_schedule(schedule_id)
        
        return jsonify({
            'success': True,
            'message': 'Schedule updated successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@schedule_bp.route('/schedule_bot/<int:schedule_id>', methods=['DELETE'])
@login_required
def delete_schedule(schedule_id):
    """
    Delete a schedule
    """
    try:
        user_id = session.get("user", {}).get("id")
        
        schedule = db.session.get(BotSchedule, schedule_id)
        if not schedule:
            return jsonify({'error': 'Schedule not found'}), 404
        
        # Check permissions
        user = db.session.get(User, user_id)
        if user.organization_id != schedule.bot.organization_id:
            return jsonify({'error': 'Unauthorized'}), 403
        
        # Remove from APScheduler
        scheduler_service.remove_schedule(schedule_id)
        
        # Delete from database
        db.session.delete(schedule)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Schedule deleted successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@schedule_bp.route('/schedule_bot/<int:schedule_id>/pause', methods=['POST'])
@login_required
def pause_schedule(schedule_id):
    try:
        schedule = db.session.get(BotSchedule, schedule_id)
        if not schedule:
            return jsonify({'error': 'Schedule not found'}), 404
        
        # Pause in APScheduler
        scheduler_service.pause_schedule(schedule_id)

        # Update DB
        schedule.is_active = False
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Schedule paused',
            'schedule_id': schedule_id,
            'is_active': schedule.is_active
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500



@schedule_bp.route('/schedule_bot/<int:schedule_id>/resume', methods=['POST'])
@login_required
def resume_schedule(schedule_id):
    try:
        schedule = db.session.get(BotSchedule, schedule_id)
        if not schedule:
            return jsonify({'error': 'Schedule not found'}), 404
        
        scheduler_service.resume_schedule(schedule_id)

        schedule.is_active = True
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Schedule resumed',
            'schedule_id': schedule_id,
            'is_active': schedule.is_active
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500



@schedule_bp.route('/execution/<int:execution_id>', methods=['GET'])
@login_required
def get_execution_status(execution_id):
    """
    Get status of a bot execution
    """
    try:
        execution = db.session.get(BotExecution, execution_id)
        if not execution:
            return jsonify({'error': 'Execution not found'}), 404
        
        # Check permissions
        user_id = request.user_id
        user = db.session.get(User, user_id)
        if user.organization_id != execution.bot.organization_id:
            return jsonify({'error': 'Unauthorized'}), 403
        
        return jsonify({
            'execution_id': execution.execution_id,
            'bot_id': execution.bot_id,
            'bot_name': execution.bot.bot_name,
            'status': execution.status.value,
            'scheduled_at': execution.scheduled_at.isoformat() if execution.scheduled_at else None,
            'started_at': execution.started_at.isoformat() if execution.started_at else None,
            'completed_at': execution.completed_at.isoformat() if execution.completed_at else None,
            'duration': (execution.completed_at - execution.started_at).total_seconds() 
                if execution.started_at and execution.completed_at else None
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@schedule_bp.route('/bot/<int:bot_id>/executions', methods=['GET'])
@login_required
def get_bot_executions(bot_id):
    """
    Get execution history for a bot
    """
    try:
        # Pagination
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        bot = db.session.get(Bot, bot_id)
        if not bot:
            return jsonify({'error': 'Bot not found'}), 404
        
        # Check permissions
        user_id = request.user_id
        user = db.session.get(User, user_id)
        if user.organization_id != bot.organization_id:
            return jsonify({'error': 'Unauthorized'}), 403
        
        executions = BotExecution.query.filter_by(bot_id=bot_id)\
            .order_by(BotExecution.created_at.desc())\
            .paginate(page=page, per_page=per_page, error_out=False)
        
        return jsonify({
            'executions': [{
                'execution_id': e.execution_id,
                'status': e.status.value,
                'scheduled_at': e.scheduled_at.isoformat() if e.scheduled_at else None,
                'started_at': e.started_at.isoformat() if e.started_at else None,
                'completed_at': e.completed_at.isoformat() if e.completed_at else None,
                'triggered_by': e.triggered_by_user.name if e.triggered_by_user else 'Scheduled',
                'schedule_name': e.schedule.name if e.schedule else 'Manual'
            } for e in executions.items],
            'total': executions.total,
            'page': page,
            'per_page': per_page,
            'pages': executions.pages
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500




@schedule_bp.route('/jobs', methods=['GET'])
@login_required
def get_all_schedules():
    try:
        schedules = BotSchedule.query.all()
        aps_jobs = scheduler_service.scheduler.get_jobs()

        # Map: schedule_id → APScheduler job
        job_map = {}

        for job in aps_jobs:
            if job.id.startswith("schedule_"):
                try:
                    sid = int(job.id.replace("schedule_", ""))
                    job_map[sid] = job
                except:
                    pass

        data = []

        for s in schedules:
            job = job_map.get(s.schedule_id)

            next_date = None
            next_time = None

            # Extract date and time correctly
            if job and job.next_run_time:
                dt = job.next_run_time  # aware datetime

                # Convert to simple string parts
                next_date = dt.strftime("%Y-%m-%d")
                next_time = dt.strftime("%H:%M")

            data.append({
                "schedule_id": s.schedule_id,
                "bot_name": s.bot.bot_name if s.bot else None,
                "next_run_date": next_date,
                "next_run_time": next_time,
                "status": "active" if s.is_active else "paused"
            })

        return jsonify({"schedules": data})

    except Exception as e:
        return jsonify({"error": str(e)}), 500