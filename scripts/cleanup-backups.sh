#!/bin/bash
# Backup Cleanup Script
# Removes old backups based on retention policy

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
CONFIG_FILE="${PROJECT_DIR}/config/backup-retention.conf"
BACKUP_DIR="${PROJECT_DIR}/backups"

# Default retention policy
KEEP_LAST_N=10
KEEP_DAILY_DAYS=7
KEEP_WEEKLY_DAYS=30
KEEP_MONTHLY_DAYS=365

# Load configuration if it exists
if [ -f "$CONFIG_FILE" ]; then
    source "$CONFIG_FILE"
fi

# Function to log messages
log_message() {
    local level="$1"
    shift
    local message="$*"
    local timestamp=$(date +"%Y-%m-%d %H:%M:%S")
    echo "[$timestamp] [$level] $message"
}

# Function to get backup date from filename
get_backup_date() {
    local filename="$1"
    # Extract date from filename: minecraft_backup_YYYYMMDD_HHMMSS.tar.gz
    local date_part=$(echo "$filename" | grep -oP 'minecraft_backup_\K\d{8}' || echo "")
    if [ -n "$date_part" ]; then
        echo "${date_part:0:4}-${date_part:4:2}-${date_part:6:2}"
    fi
}

# Function to check if backup is daily/weekly/monthly
classify_backup() {
    local filename="$1"
    local date_str=$(get_backup_date "$filename")

    if [ -z "$date_str" ]; then
        echo "unknown"
        return
    fi

    local day_of_month=$(date -d "$date_str" +%d 2>/dev/null || echo "")
    local day_of_week=$(date -d "$date_str" +%w 2>/dev/null || echo "")

    # Monthly backup: first day of month
    if [ "$day_of_month" = "01" ]; then
        echo "monthly"
    # Weekly backup: Sunday
    elif [ "$day_of_week" = "0" ]; then
        echo "weekly"
    else
        echo "daily"
    fi
}

# Main cleanup function
main() {
    log_message "INFO" "Starting backup cleanup"

    if [ ! -d "$BACKUP_DIR" ]; then
        log_message "WARNING" "Backup directory not found: $BACKUP_DIR"
        exit 0
    fi

    local deleted_count=0
    local kept_count=0
    local total_size_freed=0

    # Get all backup files sorted by modification time (newest first)
    local backups=($(find "$BACKUP_DIR" -name "minecraft_backup_*.tar.gz" -type f -printf '%T@ %p\n' | sort -rn | cut -d' ' -f2-))

    if [ ${#backups[@]} -eq 0 ]; then
        log_message "INFO" "No backups found to clean up"
        exit 0
    fi

    log_message "INFO" "Found ${#backups[@]} backup(s) to evaluate"

    # Keep last N backups regardless of age
    local keep_last_n=$KEEP_LAST_N
    local index=0

    for backup_file in "${backups[@]}"; do
        local filename=$(basename "$backup_file")
        local backup_type=$(classify_backup "$filename")
        local file_age_days=$(( ($(date +%s) - $(stat -c %Y "$backup_file")) / 86400 ))
        local should_keep=false

        # Always keep the last N backups
        if [ $index -lt $keep_last_n ]; then
            should_keep=true
            log_message "DEBUG" "Keeping $filename (last N: $((index + 1))/$keep_last_n)"
        # Check retention by type
        elif [ "$backup_type" = "monthly" ] && [ $file_age_days -le $KEEP_MONTHLY_DAYS ]; then
            should_keep=true
            log_message "DEBUG" "Keeping $filename (monthly, age: ${file_age_days}d)"
        elif [ "$backup_type" = "weekly" ] && [ $file_age_days -le $KEEP_WEEKLY_DAYS ]; then
            should_keep=true
            log_message "DEBUG" "Keeping $filename (weekly, age: ${file_age_days}d)"
        elif [ "$backup_type" = "daily" ] && [ $file_age_days -le $KEEP_DAILY_DAYS ]; then
            should_keep=true
            log_message "DEBUG" "Keeping $filename (daily, age: ${file_age_days}d)"
        fi

        if [ "$should_keep" = true ]; then
            kept_count=$((kept_count + 1))
        else
            local file_size=$(stat -c %s "$backup_file" 2>/dev/null || echo "0")
            total_size_freed=$((total_size_freed + file_size))
            rm -f "$backup_file"
            deleted_count=$((deleted_count + 1))
            log_message "INFO" "Deleted $filename (age: ${file_age_days}d, type: $backup_type)"
        fi

        index=$((index + 1))
    done

    # Format size
    local size_freed_mb=$((total_size_freed / 1024 / 1024))

    log_message "INFO" "Cleanup complete: kept $kept_count, deleted $deleted_count backup(s), freed ${size_freed_mb}MB"
}

# Run main function
main "$@"

