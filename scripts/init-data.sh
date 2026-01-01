#!/bin/bash
# =============================================================================
# POS Application - Initial Data Setup Script
# Run this script ONCE after first deployment to set up initial data
# =============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() {
    echo -e "${GREEN}[INIT]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

warn() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Configuration
SUPERUSER_EMAIL="${SUPERUSER_EMAIL:-admin@demo.com}"
SUPERUSER_PASSWORD="${SUPERUSER_PASSWORD:-changeme123}"

log "=============================================="
log "POS Application - Initial Data Setup"
log "=============================================="

# =============================================================================
# Step 1: Wait for database to be ready
# =============================================================================
log "Waiting for database to be ready..."

MAX_RETRIES=30
RETRY_COUNT=0

while ! docker-compose -f docker-compose.prod.yml exec -T db pg_isready -U ${DB_USER:-pos_user} -d ${DB_NAME:-pos_db} > /dev/null 2>&1; do
    RETRY_COUNT=$((RETRY_COUNT + 1))
    if [ $RETRY_COUNT -ge $MAX_RETRIES ]; then
        error "Database not ready after $MAX_RETRIES attempts"
        exit 1
    fi
    log "Waiting for database... (attempt $RETRY_COUNT/$MAX_RETRIES)"
    sleep 2
done

log "Database is ready!"

# =============================================================================
# Step 2: Run database migrations
# =============================================================================
log "Running database migrations..."

docker-compose -f docker-compose.prod.yml exec -T api python manage.py migrate --noinput

log "Migrations completed!"

# =============================================================================
# Step 3: Create superuser
# =============================================================================
log "Creating superuser: ${SUPERUSER_EMAIL}"

docker-compose -f docker-compose.prod.yml exec -T api python manage.py shell << EOF
from django.contrib.auth import get_user_model
User = get_user_model()

if not User.objects.filter(email='${SUPERUSER_EMAIL}').exists():
    user = User.objects.create_superuser(
        username='admin',
        email='${SUPERUSER_EMAIL}',
        password='${SUPERUSER_PASSWORD}',
        role='ADMIN'
    )
    user.is_super_admin = True
    user.save()
    print(f"Superuser created: {user.email}")
else:
    print("Superuser already exists")
EOF

# =============================================================================
# Step 4: Load demo data
# =============================================================================
log "Loading demo data..."

docker-compose -f docker-compose.prod.yml exec -T api python manage.py load_demo_data

log "Demo data loaded!"

# =============================================================================
# Step 5: Collect static files
# =============================================================================
log "Collecting static files..."

docker-compose -f docker-compose.prod.yml exec -T api python manage.py collectstatic --noinput

log "Static files collected!"

# =============================================================================
# Step 6: Set up Celery Beat scheduled tasks
# =============================================================================
log "Setting up scheduled tasks..."

docker-compose -f docker-compose.prod.yml exec -T api python manage.py shell << 'EOF'
from django_celery_beat.models import PeriodicTask, CrontabSchedule
import json

# Create schedules if they don't exist
schedule_8am, _ = CrontabSchedule.objects.get_or_create(
    minute='0', hour='8', day_of_week='*', day_of_month='*', month_of_year='*'
)

schedule_2am, _ = CrontabSchedule.objects.get_or_create(
    minute='0', hour='2', day_of_week='*', day_of_month='*', month_of_year='*'
)

schedule_230am, _ = CrontabSchedule.objects.get_or_create(
    minute='30', hour='2', day_of_week='*', day_of_month='*', month_of_year='*'
)

# Create periodic tasks
PeriodicTask.objects.get_or_create(
    name='check-stock-levels-daily',
    defaults={
        'task': 'dashboard.tasks.check_stock_levels',
        'crontab': schedule_8am,
        'enabled': True,
    }
)

PeriodicTask.objects.get_or_create(
    name='cleanup-old-exports-daily',
    defaults={
        'task': 'dashboard.tasks.cleanup_old_exports',
        'crontab': schedule_2am,
        'enabled': True,
    }
)

PeriodicTask.objects.get_or_create(
    name='cleanup-old-reports-daily',
    defaults={
        'task': 'dashboard.tasks.cleanup_old_reports',
        'crontab': schedule_230am,
        'enabled': True,
    }
)

print("Scheduled tasks configured")
EOF

log "Scheduled tasks configured!"

# =============================================================================
# Completion
# =============================================================================
log "=============================================="
log "Initial data setup completed successfully!"
log "=============================================="
log ""
log "Superuser credentials:"
log "  Email:    ${SUPERUSER_EMAIL}"
log "  Password: ${SUPERUSER_PASSWORD}"
log ""
warn "IMPORTANT: Change the superuser password immediately after first login!"
log ""
log "Demo data created:"
log "  - 1 Partner (Demo Company)"
log "  - 2 Stores (Main Store, Branch Store)"
log "  - 5 Product Categories"
log "  - 10 Sample Products"
log "  - 3 Expense Categories"
log "  - 1 Supplier"
log ""
log "You can now access the application!"
