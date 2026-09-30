#!/bin/bash
# Backup Scheduler Script for Minecraft Server
# This script can be called by cron or systemd timers

set -e

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source-path=SCRIPTDIR
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
CONFIG_FILE="${PROJECT_DIR}/config/backup-schedule.conf"

# shellcheck source=lib/notify.sh
source "${SCRIPT_DIR}/lib/notify.sh"

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
    local timestamp
    timestamp=$(date +"%Y-%m-%d %H:%M:%S")
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
            local day
            day=$(date +%w)
            local target_day=${BACKUP_WEEKLY_DAY:-0}
            [ "$day" -eq "$target_day" ] && return 0 || return 1
            ;;
        monthly)
            # Run on first day of month
            local day
            day=$(date +%d)
            [ "$day" -eq "01" ] && return 0 || return 1
            ;;
        *)
            log_message "ERROR" "Unknown backup frequency: $BACKUP_FREQUENCY"
            return 1
            ;;
    esac
}

# Function to upload a backup to whichever cloud provider is configured.
# Reads config/cloud-backup-<provider>.conf; a provider config with
# AUTO_UPLOAD="true" opts in. Offsite is best-effort: a failed upload is
# logged and notified, but does not fail the scheduled backup, since the
# local copy the rest of this run produced is still good.
upload_offsite() {
    local backup_file="$1" provider conf script status
    for provider in r2 s3 b2; do
        conf="${PROJECT_DIR}/config/cloud-backup-${provider}.conf"
        script="${SCRIPT_DIR}/cloud-backup-${provider}.sh"
        [ -f "$conf" ] || continue

        # Subshell: keep the provider config's AUTO_UPLOAD and credentials out
        # of this script's own scope and out of the next provider's check.
        status=0
        (
            # shellcheck source=/dev/null
            source "$conf"
            [ "${AUTO_UPLOAD:-false}" = "true" ] || exit 3
            "$script" upload "$backup_file"
        ) || status=$?

        case "$status" in
            0) log_message "INFO" "Uploaded $(basename "$backup_file") to ${provider}" ;;
            3) ;; # AUTO_UPLOAD not set for this provider; not an error
            *)
                log_message "ERROR" "Offsite upload to ${provider} failed"
                notify "Minecraft backup" "Local backup OK, but offsite upload to ${provider} failed" high
                ;;
        esac
    done
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

    # Check if it's the right time (if time is specified). This gate is for
    # cron, which runs the script every minute. Under systemd (which sets
    # INVOCATION_ID) the timer already decides when: its randomized delay and
    # Persistent= catch-up runs would otherwise almost never land on the
    # exact minute, and the backup would be skipped.
    if [ -n "$BACKUP_TIME" ] && [ -z "${INVOCATION_ID:-}" ]; then
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

            local latest_backup
            latest_backup="$(ls -t "${PROJECT_DIR}"/backups/minecraft_backup_*.tar.gz 2>/dev/null | head -1)"
            if [ -n "$latest_backup" ]; then
                upload_offsite "$latest_backup" >> "${PROJECT_DIR}/logs/backup-scheduler.log" 2>&1
            fi

            # Secrets archive: config, credentials, tunnel state -- not part of
            # ./data, and lost along with it on the same SD card failure.
            if [ -f "${SCRIPT_DIR}/backup-secrets.sh" ]; then
                "${SCRIPT_DIR}/backup-secrets.sh" >> "${PROJECT_DIR}/logs/backup-scheduler.log" 2>&1 || \
                    log_message "ERROR" "Secrets backup failed; see the log above"
            fi
        else
            log_message "ERROR" "Scheduled backup failed"
            notify "Minecraft backup failed" "manage.sh backup exited non-zero; check logs/backup-scheduler.log" high
            exit 1
        fi
    else
        log_message "ERROR" "manage.sh not found at ${SCRIPT_DIR}/manage.sh"
        exit 1
    fi
}

# Run main function
main "$@"
