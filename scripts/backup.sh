#!/bin/bash
# =============================================================================
# POS Application - Database Backup Script
# Runs daily via cron to backup PostgreSQL to S3
# =============================================================================

set -e

# Configuration
BACKUP_DIR="/tmp/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="pos_backup_${TIMESTAMP}.sql.gz"
S3_BUCKET="${S3_BACKUP_BUCKET:-pos-backups}"
RETENTION_DAYS=7

# Database credentials (from environment or .env)
DB_HOST="${DB_HOST:-db}"
DB_NAME="${DB_NAME:-pos_db}"
DB_USER="${DB_USER:-pos_user}"
DB_PASSWORD="${DB_PASSWORD}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1" >&2
}

warn() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1"
}

# Create backup directory
mkdir -p "$BACKUP_DIR"

log "Starting database backup..."

# Perform backup using pg_dump
export PGPASSWORD="$DB_PASSWORD"

if pg_dump -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" | gzip > "${BACKUP_DIR}/${BACKUP_FILE}"; then
    log "Database dump completed: ${BACKUP_FILE}"
    
    # Get file size
    BACKUP_SIZE=$(ls -lh "${BACKUP_DIR}/${BACKUP_FILE}" | awk '{print $5}')
    log "Backup size: ${BACKUP_SIZE}"
else
    error "Database dump failed!"
    exit 1
fi

# Upload to S3
log "Uploading to S3: s3://${S3_BUCKET}/backups/${BACKUP_FILE}"

if aws s3 cp "${BACKUP_DIR}/${BACKUP_FILE}" "s3://${S3_BUCKET}/backups/${BACKUP_FILE}" --storage-class STANDARD_IA; then
    log "Upload to S3 completed successfully"
else
    error "Failed to upload to S3!"
    exit 1
fi

# Clean up local backup
rm -f "${BACKUP_DIR}/${BACKUP_FILE}"
log "Local backup file cleaned up"

# Delete old backups from S3 (older than RETENTION_DAYS)
log "Cleaning up backups older than ${RETENTION_DAYS} days..."

CUTOFF_DATE=$(date -d "-${RETENTION_DAYS} days" +%Y-%m-%d 2>/dev/null || date -v-${RETENTION_DAYS}d +%Y-%m-%d)

aws s3 ls "s3://${S3_BUCKET}/backups/" | while read -r line; do
    FILE_DATE=$(echo "$line" | awk '{print $1}')
    FILE_NAME=$(echo "$line" | awk '{print $4}')
    
    if [[ "$FILE_DATE" < "$CUTOFF_DATE" ]] && [[ -n "$FILE_NAME" ]]; then
        log "Deleting old backup: ${FILE_NAME}"
        aws s3 rm "s3://${S3_BUCKET}/backups/${FILE_NAME}"
    fi
done

log "Backup process completed successfully!"

# Optional: Send notification (uncomment if needed)
# curl -X POST -H 'Content-type: application/json' \
#     --data '{"text":"POS Database backup completed successfully"}' \
#     "$SLACK_WEBHOOK_URL"
