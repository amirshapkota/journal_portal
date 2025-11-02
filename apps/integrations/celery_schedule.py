"""
Celery Beat configuration for periodic tasks.

Add this to your settings.py:

from apps.integrations.celery_schedule import CELERY_BEAT_SCHEDULE
"""

from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    # Sync all journals hourly (each journal syncs based on its own interval)
    'sync-all-journals-hourly': {
        'task': 'apps.integrations.tasks.sync_all_journals',
        'schedule': crontab(minute=0),  # Every hour at minute 0
        'options': {
            'expires': 3600,  # Task expires after 1 hour
        }
    },
    
    # Check journal sync health daily at 2 AM
    'check-journal-sync-health': {
        'task': 'apps.integrations.tasks.check_journal_sync_health',
        'schedule': crontab(hour=2, minute=0),  # Daily at 2:00 AM
        'options': {
            'expires': 86400,  # Task expires after 24 hours
        }
    },
    
    # Cleanup old logs weekly on Sunday at 4 AM
    'cleanup-sync-logs-weekly': {
        'task': 'apps.integrations.tasks.cleanup_old_sync_logs',
        'schedule': crontab(hour=4, minute=0, day_of_week='sunday'),
    },
}
