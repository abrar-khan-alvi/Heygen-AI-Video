"""
Celery tasks for videogen.

Add to settings.py:
from celery.schedules import crontab
CELERY_BEAT_SCHEDULE = {
    'sync-avatars-weekly': {
        'task': 'videogen.tasks.sync_avatars_task',
        'schedule': crontab(hour=3, minute=0, day_of_week=1),
    },
}
"""

import logging
from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(name="videogen.tasks.sync_avatars_task")
def sync_avatars_task():
    from django.core.management import call_command
    logger.info("Starting weekly avatar sync...")
    try:
        call_command("sync_avatars")
        logger.info("Avatar sync completed.")
        return "Avatar sync completed."
    except Exception as e:
        logger.error(f"Avatar sync failed: {e}")
        raise