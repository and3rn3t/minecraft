#!/bin/bash
# Per-World Backup Scheduler
# Handles scheduled backups for individual worlds

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
CONFIG_FILE="${PROJECT_DIR}/config/world-backup-schedule.conf"
WORLDS_DIR="${PROJECT_DIR}/data"
BACKUP_DIR="${PROJECT_DIR}/backups/worlds"

# Default configuration
DEFAULT_BACKUP_ENABLED=true
DEFAULT_BACKUP_FREQUENCY=daily
DEFAULT_BACKUP_TIME="02:00"
DEFAULT_BACKUP_RETENTION_DAYS=7

# Load configuration if it exists
if [ -f "$CONFIG_FILE" ]; then
    source "$CONFIG_FILE"
fi

# Ensure backup directory exists
mkdir -p "$BACKUP_DIR"

# Function to get world backup config
get_world_backup_config() {
    local world_name="$1"
    local setting="$2"

    # Check for world-specific setting
    local world_setting="WORLD_${world_name}_${setting}"
    local value=$(eval echo \$${world_setting})

    if [ -n "$value" ]; then
        echo "$value"
    else
        # Use default
        local default_setting="DEFAULT_BACKUP_${setting}"
        eval echo \$${default_setting}
    fi
}

# Function to check if backup should run for world
should_backup_world() {
    local world_name="$1"

    local enabled=$(get_world_backup_config "$world_name" "ENABLED")
    if [ "$enabled" != "true" ]; then
        return 1
    fi

    local frequency=$(get_world_backup_config "$world_name" "FREQUENCY")
    local current_time=$(date +"%H:%M")
    local scheduled_time=$(get_world_backup_config "$world_name" "TIME")

    case "$frequency" in
        daily)
            # Check if it's the right time
            if [ "$current_time" = "$scheduled_time" ]; then
                return 0
            fi
            ;;
        weekly)
            # Run on Sunday
            local day=$(date +%w)
            if [ "$day" -eq "0" ] && [ "$current_time" = "$scheduled_time" ]; then
                return 0
            fi
            ;;
        monthly)
            # Run on 1st of month
            local day=$(date +%d)
            if [ "$day" -eq "01" ] && [ "$current_time" = "$scheduled_time" ]; then
                return 0
            fi
            ;;
        manual)
            return 1
            ;;
    esac

    return 1
}

# Function to backup a world
backup_world_scheduled() {
    local world_name="$1"
    local world_path="${WORLDS_DIR}/${world_name}"

    if [ ! -d "$world_path" ] || [ ! -f "${world_path}/level.dat" ]; then
        return 1
    fi

    echo -e "${BLUE}Backing up world: $world_name${NC}"

    # Create backup
    local backup_file="${BACKUP_DIR}/world_${world_name}_$(date +%Y%m%d_%H%M%S).tar.gz"
    tar -czf "$backup_file" -C "$WORLDS_DIR" "$world_name" 2>/dev/null

    if [ $? -eq 0 ]; then
        local backup_size=$(du -sh "$backup_file" 2>/dev/null | cut -f1)
        echo -e "${GREEN}World backed up: $backup_file ($backup_size)${NC}"

        # Clean up old backups
        cleanup_old_backups "$world_name"
        return 0
    else
        echo -e "${RED}Backup failed: $world_name${NC}"
        return 1
    fi
}

# Function to cleanup old backups
cleanup_old_backups() {
    local world_name="$1"
    local retention_days=$(get_world_backup_config "$world_name" "RETENTION_DAYS")
    retention_days=${retention_days:-$DEFAULT_BACKUP_RETENTION_DAYS}

    if [ -d "$BACKUP_DIR" ]; then
        find "$BACKUP_DIR" -name "world_${world_name}_*.tar.gz" -type f -mtime +$retention_days -delete
    fi
}

# Function to run scheduled backups for all worlds
run_scheduled_backups() {
    echo -e "${BLUE}Running scheduled world backups...${NC}"
    echo ""

    local backed_up=0
    local skipped=0

    # Find all worlds
    for world_dir in "$WORLDS_DIR"/world*; do
        if [ -d "$world_dir" ] && [ -f "${world_dir}/level.dat" ]; then
            local world_name=$(basename "$world_dir")

            if should_backup_world "$world_name"; then
                if backup_world_scheduled "$world_name"; then
                    backed_up=$((backed_up + 1))
                fi
            else
                skipped=$((skipped + 1))
            fi
        fi
    done

    echo ""
    echo -e "${GREEN}Backup complete: $backed_up backed up, $skipped skipped${NC}"
}

# Function to backup all worlds
backup_all_worlds() {
    echo -e "${BLUE}Backing up all worlds...${NC}"
    echo ""

    local backed_up=0

    for world_dir in "$WORLDS_DIR"/world*; do
        if [ -d "$world_dir" ] && [ -f "${world_dir}/level.dat" ]; then
            local world_name=$(basename "$world_dir")
            local enabled=$(get_world_backup_config "$world_name" "ENABLED")

            if [ "$enabled" = "true" ]; then
                if backup_world_scheduled "$world_name"; then
                    backed_up=$((backed_up + 1))
                fi
            fi
        fi
    done

    echo ""
    echo -e "${GREEN}Backed up $backed_up world(s)${NC}"
}

# Main function
main() {
    case "${1:-}" in
        run)
            run_scheduled_backups
            ;;
        backup-all)
            backup_all_worlds
            ;;
        cleanup)
            # Cleanup old backups for all worlds
            for world_dir in "$WORLDS_DIR"/world*; do
                if [ -d "$world_dir" ] && [ -f "${world_dir}/level.dat" ]; then
                    local world_name=$(basename "$world_dir")
                    cleanup_old_backups "$world_name"
                fi
            done
            echo -e "${GREEN}Cleanup complete${NC}"
            ;;
        *)
            echo -e "${BLUE}Per-World Backup Scheduler${NC}"
            echo ""
            echo "Usage: $0 {run|backup-all|cleanup}"
            echo ""
            echo "Commands:"
            echo "  run        - Run scheduled backups for worlds"
            echo "  backup-all - Backup all enabled worlds now"
            echo "  cleanup    - Clean up old backups based on retention policy"
            echo ""
            exit 1
            ;;
    esac
}

# Run main function
main "$@"

