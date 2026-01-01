"""
Celery configuration for POS API.
"""
import os
from celery import Celery
from celery.schedules import crontab

# Set the default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'main.settings')

app = Celery('pos_api')

# Load config from Django settings, using CELERY_ namespace
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks in all registered Django apps
app.autodiscover_tasks()

# Celery Beat schedule for periodic tasks
app.conf.beat_schedule = {
    'check-stock-levels-daily': {
        'task': 'notifications.tasks.check_stock_levels',
        'schedule': crontab(hour=8, minute=0),  # Run daily at 8 AM
    },
    'cleanup-old-exports-daily': {
        'task': 'notifications.tasks.cleanup_old_exports',
        'schedule': crontab(hour=2, minute=0),  # Run daily at 2 AM
    },
    'cleanup-old-reports-daily': {
        'task': 'dashboard.tasks.cleanup_old_reports',
        'schedule': crontab(hour=2, minute=30),  # Run daily at 2:30 AM
    },
}


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
