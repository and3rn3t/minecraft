#!/bin/bash
# Log Manager for Minecraft Server
# Handles log aggregation, parsing, indexing, and analysis

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
CONFIG_FILE="${PROJECT_DIR}/config/log-management.conf"
LOGS_DIR="${PROJECT_DIR}/logs"
INDEX_DIR="${LOGS_DIR}/index"
ARCHIVE_DIR="${LOGS_DIR}/archive"
SERVER_LOG_DIR="${PROJECT_DIR}/data/logs"

# Default configuration
LOG_ROTATION_ENABLED=true
LOG_RETENTION_DAYS=30
MAX_LOG_SIZE_MB=100
INDEX_ENABLED=true
ERROR_DETECTION_ENABLED=true
SEARCH_ENABLED=true

# Load configuration if it exists
if [ -f "$CONFIG_FILE" ]; then
    source "$CONFIG_FILE"
fi

# Ensure directories exist
mkdir -p "$LOGS_DIR" "$INDEX_DIR" "$ARCHIVE_DIR" "$SERVER_LOG_DIR"

# Function to log messages
log_message() {
    local level="$1"
    shift
    local message="$*"
    local timestamp=$(date +"%Y-%m-%d %H:%M:%S")
    echo "[$timestamp] [$level] $message" | tee -a "${LOGS_DIR}/log-manager.log"
}

# Function to get server logs from Docker
get_server_logs() {
    local lines=${1:-1000}
    if docker ps | grep -q minecraft-server; then
        docker logs minecraft-server --tail "$lines" 2>/dev/null || echo ""
    else
        echo ""
    fi
}

# Function to get server log files
get_server_log_files() {
    # Check for latest.log and other log files in server directory
    local log_files=()

    if [ -f "${SERVER_LOG_DIR}/latest.log" ]; then
        log_files+=("${SERVER_LOG_DIR}/latest.log")
    fi

    # Find all .log.gz files (archived logs)
    while IFS= read -r -d '' file; do
        log_files+=("$file")
    done < <(find "$SERVER_LOG_DIR" -name "*.log.gz" -type f -print0 2>/dev/null || true)

    # Find all numbered log files
    while IFS= read -r -d '' file; do
        log_files+=("$file")
    done < <(find "$SERVER_LOG_DIR" -name "*.log" -type f -print0 2>/dev/null || true)

    printf '%s\n' "${log_files[@]}"
}

# Function to parse log line and extract information
parse_log_line() {
    local line="$1"

    # Minecraft log format: [HH:MM:SS] [LEVEL/THREAD] MESSAGE
    # Example: [12:34:56] [Server thread/INFO] Starting minecraft server version 1.20.4

    local timestamp=""
    local level=""
    local thread=""
    local message=""

    # Extract timestamp [HH:MM:SS]
    if [[ "$line" =~ \[([0-9]{2}:[0-9]{2}:[0-9]{2})\] ]]; then
        timestamp="${BASH_REMATCH[1]}"
    fi

    # Extract level and thread [LEVEL/THREAD]
    if [[ "$line" =~ \[([^]]+)/([^]]+)\] ]]; then
        level="${BASH_REMATCH[1]}"
        thread="${BASH_REMATCH[2]}"
    fi

    # Extract message (everything after the last bracket)
    if [[ "$line" =~ \][[:space:]]*(.+)$ ]]; then
        message="${BASH_REMATCH[1]}"
    fi

    # Output as JSON-like structure (tab-separated for easy parsing)
    echo -e "${timestamp}\t${level}\t${thread}\t${message}"
}

# Function to index logs
index_logs() {
    if [ "$INDEX_ENABLED" != "true" ]; then
        return 0
    fi

    log_message "INFO" "Starting log indexing..."

    local index_file="${INDEX_DIR}/log_index_$(date +%Y%m%d).txt"
    local temp_index=$(mktemp)
    local line_count=0

    # Index server log files
    while IFS= read -r log_file; do
        if [ -f "$log_file" ]; then
            log_message "DEBUG" "Indexing: $log_file"

            # Process log file
            if [[ "$log_file" == *.gz ]]; then
                zcat "$log_file" 2>/dev/null | while IFS= read -r line; do
                    parse_log_line "$line" >> "$temp_index"
                    line_count=$((line_count + 1))
                done || true
            else
                while IFS= read -r line; do
                    parse_log_line "$line" >> "$temp_index"
                    line_count=$((line_count + 1))
                done < "$log_file" || true
            fi
        fi
    done < <(get_server_log_files)

    # Also index Docker logs
    get_server_logs 10000 | while IFS= read -r line; do
        if [ -n "$line" ]; then
            parse_log_line "$line" >> "$temp_index"
            line_count=$((line_count + 1))
        fi
    done

    # Sort and deduplicate index
    sort -u "$temp_index" > "$index_file"
    rm -f "$temp_index"

    log_message "INFO" "Indexed $line_count log entries to $index_file"
}

# Function to detect error patterns
detect_errors() {
    if [ "$ERROR_DETECTION_ENABLED" != "true" ]; then
        return 0
    fi

    log_message "INFO" "Detecting error patterns..."

    local error_file="${LOGS_DIR}/errors_$(date +%Y%m%d).txt"
    local error_patterns=(
        "ERROR"
        "FATAL"
        "Exception"
        "java.lang"
        "OutOfMemoryError"
        "StackOverflowError"
        "NullPointerException"
        "ClassNotFoundException"
        "NoSuchMethodError"
        "failed"
        "crash"
        "timeout"
        "connection refused"
        "can't keep up"
        "WARN.*lag"
    )

    > "$error_file"  # Clear error file

    # Check server log files
    while IFS= read -r log_file; do
        if [ -f "$log_file" ]; then
            for pattern in "${error_patterns[@]}"; do
                if [[ "$log_file" == *.gz ]]; then
                    zcat "$log_file" 2>/dev/null | grep -iE "$pattern" >> "$error_file" || true
                else
                    grep -iE "$pattern" "$log_file" >> "$error_file" || true
                fi
            done
        fi
    done < <(get_server_log_files)

    # Check Docker logs
    get_server_logs 10000 | grep -iE "$(IFS='|'; echo "${error_patterns[*]}")" >> "$error_file" || true

    # Count errors
    local error_count=$(wc -l < "$error_file" 2>/dev/null || echo "0")

    if [ "$error_count" -gt 0 ]; then
        log_message "WARNING" "Found $error_count error(s) - see $error_file"

        # Show summary of unique errors
        echo -e "${YELLOW}Error Summary:${NC}"
        sort "$error_file" | uniq -c | sort -rn | head -10
    else
        log_message "INFO" "No errors detected"
    fi
}

# Function to rotate logs
rotate_logs() {
    if [ "$LOG_ROTATION_ENABLED" != "true" ]; then
        return 0
    fi

    log_message "INFO" "Starting log rotation..."

    # Rotate server log files
    if [ -f "${SERVER_LOG_DIR}/latest.log" ]; then
        local log_size=$(stat -f%z "${SERVER_LOG_DIR}/latest.log" 2>/dev/null || stat -c%s "${SERVER_LOG_DIR}/latest.log" 2>/dev/null || echo "0")
        local max_size=$((MAX_LOG_SIZE_MB * 1024 * 1024))

        if [ "$log_size" -gt "$max_size" ]; then
            log_message "INFO" "Rotating latest.log (size: $((log_size / 1024 / 1024))MB)"

            # Compress and archive
            local archive_name="latest_$(date +%Y%m%d_%H%M%S).log.gz"
            gzip -c "${SERVER_LOG_DIR}/latest.log" > "${ARCHIVE_DIR}/${archive_name}"

            # Clear latest.log (server will create new one)
            > "${SERVER_LOG_DIR}/latest.log"

            log_message "INFO" "Archived to ${ARCHIVE_DIR}/${archive_name}"
        fi
    fi

    # Clean up old archived logs based on retention policy
    if [ -d "$ARCHIVE_DIR" ]; then
        find "$ARCHIVE_DIR" -name "*.log.gz" -type f -mtime +$LOG_RETENTION_DAYS -delete
        log_message "INFO" "Cleaned up logs older than $LOG_RETENTION_DAYS days"
    fi

    # Clean up old index files
    if [ -d "$INDEX_DIR" ]; then
        find "$INDEX_DIR" -name "log_index_*.txt" -type f -mtime +$LOG_RETENTION_DAYS -delete
    fi

    # Clean up old error files
    if [ -d "$LOGS_DIR" ]; then
        find "$LOGS_DIR" -name "errors_*.txt" -type f -mtime +$LOG_RETENTION_DAYS -delete
    fi
}

# Function to search logs
search_logs() {
    if [ "$SEARCH_ENABLED" != "true" ]; then
        echo "Log search is disabled"
        return 1
    fi

    local query="$1"
    local max_results=${2:-100}

    if [ -z "$query" ]; then
        echo -e "${RED}Error: Search query required${NC}"
        echo "Usage: $0 search <query> [max_results]"
        return 1
    fi

    echo -e "${BLUE}Searching logs for: $query${NC}"

    local result_count=0

    # Search in index files (faster)
    if [ -d "$INDEX_DIR" ]; then
        find "$INDEX_DIR" -name "log_index_*.txt" -type f | sort -r | while read -r index_file; do
            if [ "$result_count" -ge "$max_results" ]; then
                break
            fi

            grep -iE "$query" "$index_file" | while IFS=$'\t' read -r timestamp level thread message; do
                if [ "$result_count" -lt "$max_results" ]; then
                    echo -e "${GREEN}[$timestamp]${NC} [${YELLOW}$level${NC}] $message"
                    result_count=$((result_count + 1))
                fi
            done
        done
    fi

    # Also search in current logs
    get_server_logs 1000 | grep -iE "$query" | head -n $((max_results - result_count)) | while read -r line; do
        echo "$line"
        result_count=$((result_count + 1))
    done

    echo -e "${BLUE}Found $result_count result(s)${NC}"
}

# Function to show log statistics
show_statistics() {
    echo -e "${BLUE}Log Statistics${NC}"
    echo "=============="

    # Count log files
    local log_file_count=$(get_server_log_files | wc -l)
    echo "Log files: $log_file_count"

    # Total log size
    local total_size=0
    while IFS= read -r log_file; do
        if [ -f "$log_file" ]; then
            local size=$(stat -f%z "$log_file" 2>/dev/null || stat -c%s "$log_file" 2>/dev/null || echo "0")
            total_size=$((total_size + size))
        fi
    done < <(get_server_log_files)

    echo "Total log size: $((total_size / 1024 / 1024))MB"

    # Archive count
    local archive_count=$(find "$ARCHIVE_DIR" -name "*.log.gz" -type f 2>/dev/null | wc -l)
    echo "Archived logs: $archive_count"

    # Index count
    local index_count=$(find "$INDEX_DIR" -name "log_index_*.txt" -type f 2>/dev/null | wc -l)
    echo "Index files: $index_count"

    # Error count (today)
    local error_file="${LOGS_DIR}/errors_$(date +%Y%m%d).txt"
    if [ -f "$error_file" ]; then
        local error_count=$(wc -l < "$error_file")
        echo "Errors today: $error_count"
    else
        echo "Errors today: 0"
    fi
}

# Main function
main() {
    case "${1:-}" in
        index)
            index_logs
            ;;
        errors)
            detect_errors
            ;;
        rotate)
            rotate_logs
            ;;
        search)
            search_logs "$2" "$3"
            ;;
        stats)
            show_statistics
            ;;
        all)
            rotate_logs
            index_logs
            detect_errors
            show_statistics
            ;;
        *)
            echo -e "${BLUE}Log Manager for Minecraft Server${NC}"
            echo ""
            echo "Usage: $0 {index|errors|rotate|search|stats|all}"
            echo ""
            echo "Commands:"
            echo "  index          - Parse and index logs"
            echo "  errors         - Detect error patterns"
            echo "  rotate         - Rotate and archive logs"
            echo "  search <query> - Search logs for query"
            echo "  stats          - Show log statistics"
            echo "  all            - Run all operations (rotate, index, errors, stats)"
            echo ""
            exit 1
            ;;
    esac
}

# Run main function
main "$@"

