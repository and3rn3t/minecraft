#!/bin/bash
# Backup Scheduler Script for Minecraft Server
# This script can be called by cron or systemd timers

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
CONFIG_FILE="${PROJECT_DIR}/config/backup-schedule.conf"

# Default configuration
BACKUP_ENABLED=true
BACKUP_TIME="03:00"
BACKUP_FREQUENCY="daily"

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
    echo "[$timestamp] [$level] $message" | tee -a "${PROJECT_DIR}/logs/backup-scheduler.log"
}

# Function to check if backup should run
should_run_backup() {
    case "$BACKUP_FREQUENCY" in
        daily)
            return 0
            ;;
        weekly)
            # Run on Sunday (0) or configured day
            local day=$(date +%w)
            local target_day=${BACKUP_WEEKLY_DAY:-0}
            [ "$day" -eq "$target_day" ] && return 0 || return 1
            ;;
        monthly)
            # Run on first day of month
            local day=$(date +%d)
            [ "$day" -eq "01" ] && return 0 || return 1
            ;;
        *)
            log_message "ERROR" "Unknown backup frequency: $BACKUP_FREQUENCY"
            return 1
            ;;
    esac
}

# Main backup execution
main() {
    # Create logs directory if it doesn't exist
    mkdir -p "${PROJECT_DIR}/logs"

    log_message "INFO" "Backup scheduler started"

    if [ "$BACKUP_ENABLED" != "true" ]; then
        log_message "INFO" "Backup scheduling is disabled"
        exit 0
    fi

    # Check if backup should run based on frequency
    if ! should_run_backup; then
        log_message "INFO" "Skipping backup (not scheduled for today)"
        exit 0
    fi

    # Check if it's the right time (if time is specified)
    if [ -n "$BACKUP_TIME" ]; then
        current_time=$(date +"%H:%M")
        if [ "$current_time" != "$BACKUP_TIME" ]; then
            log_message "INFO" "Skipping backup (current time: $current_time, scheduled: $BACKUP_TIME)"
            exit 0
        fi
    fi

    log_message "INFO" "Starting scheduled backup"

    # Change to project directory
    cd "$PROJECT_DIR"

    # Run backup
    if [ -f "${SCRIPT_DIR}/manage.sh" ]; then
        if "${SCRIPT_DIR}/manage.sh" backup >> "${PROJECT_DIR}/logs/backup-scheduler.log" 2>&1; then
            log_message "INFO" "Scheduled backup completed successfully"

            # Run cleanup if retention is enabled
            if [ -f "${SCRIPT_DIR}/cleanup-backups.sh" ]; then
                log_message "INFO" "Running backup cleanup"
                "${SCRIPT_DIR}/cleanup-backups.sh" >> "${PROJECT_DIR}/logs/backup-scheduler.log" 2>&1 || true
            fi
        else
            log_message "ERROR" "Scheduled backup failed"
            exit 1
        fi
    else
        log_message "ERROR" "manage.sh not found at ${SCRIPT_DIR}/manage.sh"
        exit 1
    fi
}

# Run main function
main "$@"

