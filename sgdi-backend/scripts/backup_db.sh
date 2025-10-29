#!/bin/bash
#
# SGDI Database Backup Script
#
# This script creates a PostgreSQL database backup using pg_dump
# and stores it in the configured backup directory.
#
# Environment Variables:
# - DATABASE_URL: PostgreSQL connection URL (required)
# - BACKUP_PATH: Directory to store backups (default: /app/backups)
# - BACKUP_RETENTION_DAYS: Days to keep backups (default: 30)
#
# Usage:
#   ./scripts/backup_db.sh [backup_name]
#
# If backup_name is not provided, it will be generated automatically.

set -e  # Exit on any error

# Default values
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKUP_PATH="${BACKUP_PATH:-/app/backups}"
BACKUP_RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-30}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Parse DATABASE_URL to extract connection parameters
parse_database_url() {
    local url="$1"

    if [[ ! "$url" =~ postgresql://([^:]+):([^@]+)@([^:]+):([0-9]+)/(.+) ]]; then
        log_error "Invalid DATABASE_URL format"
        exit 1
    fi

    DB_USER="${BASH_REMATCH[1]}"
    DB_PASSWORD="${BASH_REMATCH[2]}"
    DB_HOST="${BASH_REMATCH[3]}"
    DB_PORT="${BASH_REMATCH[4]}"
    DB_NAME="${BASH_REMATCH[5]}"
}

# Generate backup filename
generate_backup_name() {
    local custom_name="$1"
    local timestamp=$(date +"%Y%m%d_%H%M%S")

    if [ -n "$custom_name" ]; then
        echo "db_backup_${custom_name}_${timestamp}.sql"
    else
        echo "db_backup_${timestamp}.sql"
    fi
}

# Create backup directory
ensure_backup_directory() {
    if [ ! -d "$BACKUP_PATH" ]; then
        log_info "Creating backup directory: $BACKUP_PATH"
        mkdir -p "$BACKUP_PATH"
    fi

    if [ ! -w "$BACKUP_PATH" ]; then
        log_error "Backup directory is not writable: $BACKUP_PATH"
        exit 1
    fi
}

# Perform database backup
perform_backup() {
    local backup_file="$1"

    log_info "Starting database backup..."
    log_info "Database: $DB_NAME on $DB_HOST:$DB_PORT"
    log_info "Backup file: $backup_file"

    # Export password for pg_dump
    export PGPASSWORD="$DB_PASSWORD"

    # Perform the backup
    if pg_dump \
        --host="$DB_HOST" \
        --port="$DB_PORT" \
        --username="$DB_USER" \
        --dbname="$DB_NAME" \
        --no-password \
        --format=custom \
        --compress=9 \
        --verbose \
        --file="$backup_file"; then

        log_info "Database backup completed successfully"

        # Get backup file size
        local size_bytes=$(stat -f%z "$backup_file" 2>/dev/null || stat -c%s "$backup_file" 2>/dev/null || echo "0")
        local size_mb=$(echo "scale=2; $size_bytes / 1024 / 1024" | bc 2>/dev/null || echo "0")

        log_info "Backup file size: ${size_mb} MB"

        return 0
    else
        log_error "Database backup failed"
        return 1
    fi
}

# Clean up old backups
cleanup_old_backups() {
    log_info "Cleaning up old backups (retention: ${BACKUP_RETENTION_DAYS} days)..."

    local cutoff_date=$(date -d "${BACKUP_RETENTION_DAYS} days ago" +%Y%m%d 2>/dev/null ||
                       date -v-${BACKUP_RETENTION_DAYS}d +%Y%m%d 2>/dev/null ||
                       echo "")

    if [ -z "$cutoff_date" ]; then
        log_warn "Could not calculate cutoff date for cleanup"
        return
    fi

    local deleted_count=0
    local total_size_saved=0

    # Find and delete old backups
    for backup_file in "$BACKUP_PATH"/db_backup_*.sql; do
        if [ -f "$backup_file" ]; then
            local file_date=$(basename "$backup_file" | sed -E 's/db_backup_[^_]+_([0-9]{8})_([0-9]{6})\.sql/\1/')
            if [ "$file_date" -lt "$cutoff_date" ] 2>/dev/null; then
                local size_bytes=$(stat -f%z "$backup_file" 2>/dev/null || stat -c%s "$backup_file" 2>/dev/null || echo "0")
                rm -f "$backup_file"
                ((deleted_count++))
                total_size_saved=$((total_size_saved + size_bytes))
            fi
        fi
    done

    if [ $deleted_count -gt 0 ]; then
        local size_mb=$(echo "scale=2; $total_size_saved / 1024 / 1024" | bc 2>/dev/null || echo "0")
        log_info "Cleaned up $deleted_count old backups, saved ${size_mb} MB"
    else
        log_info "No old backups to clean up"
    fi
}

# Verify backup integrity
verify_backup() {
    local backup_file="$1"

    log_info "Verifying backup integrity..."

    # Try to list contents of the backup
    if pg_restore --list "$backup_file" >/dev/null 2>&1; then
        log_info "Backup integrity check passed"
        return 0
    else
        log_error "Backup integrity check failed"
        return 1
    fi
}

# Main function
main() {
    local custom_name="$1"

    echo "SGDI Database Backup Script"
    echo "==========================="

    # Check if DATABASE_URL is set
    if [ -z "$DATABASE_URL" ]; then
        log_error "DATABASE_URL environment variable is required"
        exit 1
    fi

    # Parse database connection
    parse_database_url "$DATABASE_URL"

    # Ensure backup directory exists
    ensure_backup_directory

    # Generate backup filename
    local backup_name=$(generate_backup_name "$custom_name")
    local backup_file="$BACKUP_PATH/$backup_name"

    log_info "Backup configuration:"
    log_info "  Database: $DB_NAME"
    log_info "  Host: $DB_HOST:$DB_PORT"
    log_info "  User: $DB_USER"
    log_info "  Backup path: $BACKUP_PATH"
    log_info "  Backup file: $backup_name"
    log_info "  Retention: ${BACKUP_RETENTION_DAYS} days"

    # Perform the backup
    if perform_backup "$backup_file"; then
        # Verify backup integrity
        if verify_backup "$backup_file"; then
            log_info "✅ Database backup completed successfully!"
            log_info "Backup location: $backup_file"

            # Clean up old backups
            cleanup_old_backups

            exit 0
        else
            log_error "Backup verification failed"
            rm -f "$backup_file"
            exit 1
        fi
    else
        log_error "Backup failed"
        exit 1
    fi
}

# Check if script is being run directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi