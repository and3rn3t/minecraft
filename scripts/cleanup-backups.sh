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
    local timestamp
    timestamp=$(date +"%Y-%m-%d %H:%M:%S")
    echo "[$timestamp] [$level] $message"
}

# Function to print a file's modification time as a Unix epoch, on GNU stat
# (the Pi, CI) or BSD stat (a Mac running this by hand).
file_mtime_epoch() {
    stat -c %Y "$1" 2>/dev/null || stat -f %m "$1" 2>/dev/null
}

# Function to print a file's size in bytes, portably (see file_mtime_epoch)
file_size_bytes() {
    stat -c %s "$1" 2>/dev/null || stat -f %z "$1" 2>/dev/null
}

# Function to get backup date from filename
get_backup_date() {
    local filename="$1"
    # Extract date from filename: minecraft_backup_YYYYMMDD_HHMMSS.tar.gz or
    # minecraft_secrets_YYYYMMDD_HHMMSS.tar.age (backup-secrets.sh).
    # Bash's own regex matching, not `grep -P`: BSD grep (macOS) has no -P.
    local date_part=""
    if [[ "$filename" =~ minecraft_(backup|secrets)_([0-9]{8})_ ]]; then
        date_part="${BASH_REMATCH[2]}"
    fi
    if [ -n "$date_part" ]; then
        echo "${date_part:0:4}-${date_part:4:2}-${date_part:6:2}"
    fi
}

# Function to print one field of a YYYY-MM-DD date, on GNU date (the Pi, CI)
# or BSD date (a Mac running this by hand).
date_field() {
    local date_str="$1" fmt="$2"
    date -d "$date_str" "+$fmt" 2>/dev/null || date -j -f "%Y-%m-%d" "$date_str" "+$fmt" 2>/dev/null
}

# Function to check if backup is daily/weekly/monthly
classify_backup() {
    local filename="$1"
    local date_str
    date_str=$(get_backup_date "$filename")

    if [ -z "$date_str" ]; then
        echo "unknown"
        return
    fi

    local day_of_month
    day_of_month=$(date_field "$date_str" %d)
    local day_of_week
    day_of_week=$(date_field "$date_str" %w)

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

    # Get all backup and secrets-archive files sorted by modification time
    # (newest first). Built by hand rather than `find -printf`, a GNU-only
    # flag BSD find (macOS) rejects. World backups and secrets archives are
    # created together each run (backup-scheduler.sh), so they share one
    # retention pass; without this, secrets archives accumulated forever.
    local backups=() f
    while IFS= read -r f; do
        backups+=("${f#* }")
    done < <(
        for f in "$BACKUP_DIR"/minecraft_backup_*.tar.gz "$BACKUP_DIR"/minecraft_secrets_*.tar.age; do
            [ -f "$f" ] || continue
            printf '%s %s\n' "$(file_mtime_epoch "$f")" "$f"
        done | sort -rn
    )

    if [ ${#backups[@]} -eq 0 ]; then
        log_message "INFO" "No backups found to clean up"
        exit 0
    fi

    log_message "INFO" "Found ${#backups[@]} backup(s) to evaluate"

    # Keep last N backups regardless of age
    local keep_last_n=$KEEP_LAST_N
    local index=0

    for backup_file in "${backups[@]}"; do
        local filename
        filename=$(basename "$backup_file")
        local backup_type
        backup_type=$(classify_backup "$filename")
        local file_age_days
        file_age_days=$(( ($(date +%s) - $(file_mtime_epoch "$backup_file")) / 86400 ))
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
            local file_size
            file_size=$(file_size_bytes "$backup_file" 2>/dev/null || echo "0")
            total_size_freed=$((total_size_freed + file_size))
            rm -f "$backup_file"
            deleted_count=$((deleted_count + 1))
            log_message "INFO" "Deleted $filename (age: ${file_age_days}d, type: $backup_type)"
        fi

        index=$((index + 1))
    done

    # Format size
    local size_freed_mb
    size_freed_mb=$((total_size_freed / 1024 / 1024))

    log_message "INFO" "Cleanup complete: kept $kept_count, deleted $deleted_count backup(s), freed ${size_freed_mb}MB"
}

# Run main function
main "$@"
