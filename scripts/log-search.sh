#!/bin/bash
# Log Search Script for Minecraft Server
# Provides advanced search capabilities for server logs

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LOGS_DIR="${PROJECT_DIR}/logs"
INDEX_DIR="${LOGS_DIR}/index"
ARCHIVE_DIR="${LOGS_DIR}/archive"
SERVER_LOG_DIR="${PROJECT_DIR}/data/logs"

# Function to search in log files
search_in_files() {
    local query="$1"
    local max_results=${2:-50}
    local case_sensitive=${3:-false}
    local grep_flags="-i"

    if [ "$case_sensitive" = "true" ]; then
        grep_flags=""
    fi

    local count=0

    # Search in latest.log
    if [ -f "${SERVER_LOG_DIR}/latest.log" ]; then
        while IFS= read -r line; do
            if [ "$count" -ge "$max_results" ]; then
                break
            fi
            if echo "$line" | grep -qE $grep_flags "$query"; then
                echo -e "${CYAN}[latest.log]${NC} $line"
                count=$((count + 1))
            fi
        done < "${SERVER_LOG_DIR}/latest.log"
    fi

    # Search in archived logs (newest first)
    if [ -d "$ARCHIVE_DIR" ]; then
        find "$ARCHIVE_DIR" -name "*.log.gz" -type f -printf '%T@ %p\n' | \
            sort -rn | cut -d' ' -f2- | while read -r archive_file; do
            if [ "$count" -ge "$max_results" ]; then
                break
            fi

            local archive_name=$(basename "$archive_file")
            zcat "$archive_file" 2>/dev/null | grep $grep_flags -E "$query" | while IFS= read -r line; do
                if [ "$count" -lt "$max_results" ]; then
                    echo -e "${YELLOW}[$archive_name]${NC} $line"
                    count=$((count + 1))
                fi
            done
        done
    fi

    # Search in Docker logs
    if docker ps | grep -q minecraft-server; then
        docker logs minecraft-server 2>/dev/null | grep $grep_flags -E "$query" | head -n $((max_results - count)) | while IFS= read -r line; do
            echo -e "${GREEN}[docker]${NC} $line"
            count=$((count + 1))
        done
    fi

    echo "$count"
}

# Function to search by date range
search_by_date() {
    local query="$1"
    local start_date="$2"
    local end_date="$3"
    local max_results=${4:-50}

    echo -e "${BLUE}Searching logs from $start_date to $end_date${NC}"

    # Convert dates to timestamps for comparison
    local start_ts=$(date -d "$start_date" +%s 2>/dev/null || echo "0")
    local end_ts=$(date -d "$end_date" +%s 2>/dev/null || echo "0")

    local count=0

    # Search in archived logs
    if [ -d "$ARCHIVE_DIR" ]; then
        find "$ARCHIVE_DIR" -name "*.log.gz" -type f | while read -r archive_file; do
            if [ "$count" -ge "$max_results" ]; then
                break
            fi

            # Extract date from filename (latest_YYYYMMDD_HHMMSS.log.gz)
            local filename=$(basename "$archive_file")
            if [[ "$filename" =~ ([0-9]{8}) ]]; then
                local file_date="${BASH_REMATCH[1]}"
                local file_ts=$(date -d "${file_date:0:4}-${file_date:4:2}-${file_date:6:2}" +%s 2>/dev/null || echo "0")

                if [ "$file_ts" -ge "$start_ts" ] && [ "$file_ts" -le "$end_ts" ]; then
                    zcat "$archive_file" 2>/dev/null | grep -iE "$query" | while IFS= read -r line; do
                        if [ "$count" -lt "$max_results" ]; then
                            echo -e "${YELLOW}[$filename]${NC} $line"
                            count=$((count + 1))
                        fi
                    done
                fi
            fi
        done
    fi

    echo "$count"
}

# Function to search by log level
search_by_level() {
    local level="$1"
    local max_results=${2:-50}

    echo -e "${BLUE}Searching for $level level messages${NC}"

    local count=0

    # Search in latest.log
    if [ -f "${SERVER_LOG_DIR}/latest.log" ]; then
        grep -iE "\[.*/$level\]" "${SERVER_LOG_DIR}/latest.log" | head -n "$max_results" | while IFS= read -r line; do
            echo "$line"
            count=$((count + 1))
        done
    fi

    # Search in archived logs
    if [ -d "$ARCHIVE_DIR" ]; then
        find "$ARCHIVE_DIR" -name "*.log.gz" -type f | while read -r archive_file; do
            if [ "$count" -ge "$max_results" ]; then
                break
            fi

            zcat "$archive_file" 2>/dev/null | grep -iE "\[.*/$level\]" | while IFS= read -r line; do
                if [ "$count" -lt "$max_results" ]; then
                    echo "$line"
                    count=$((count + 1))
                fi
            done
        done
    fi

    echo "$count"
}

# Function to show search help
show_help() {
    echo -e "${BLUE}Log Search for Minecraft Server${NC}"
    echo ""
    echo "Usage: $0 [options] <query>"
    echo ""
    echo "Options:"
    echo "  -c, --case-sensitive    Case-sensitive search"
    echo "  -n, --max-results NUM   Maximum number of results (default: 50)"
    echo "  -l, --level LEVEL       Search by log level (INFO, WARN, ERROR, etc.)"
    echo "  -d, --date DATE         Search on specific date (YYYY-MM-DD)"
    echo "  -r, --range START END   Search date range (YYYY-MM-DD YYYY-MM-DD)"
    echo "  -h, --help              Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 'player joined'                    # Search for 'player joined'"
    echo "  $0 -n 100 'error'                     # Search for 'error', max 100 results"
    echo "  $0 -l ERROR                           # Show all ERROR level messages"
    echo "  $0 -d 2025-01-15 'crash'              # Search for 'crash' on Jan 15, 2025"
    echo "  $0 -r 2025-01-01 2025-01-31 'login'  # Search for 'login' in January 2025"
    echo ""
}

# Main function
main() {
    local query=""
    local max_results=50
    local case_sensitive=false
    local level=""
    local date=""
    local start_date=""
    local end_date=""

    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -c|--case-sensitive)
                case_sensitive=true
                shift
                ;;
            -n|--max-results)
                max_results="$2"
                shift 2
                ;;
            -l|--level)
                level="$2"
                shift 2
                ;;
            -d|--date)
                date="$2"
                shift 2
                ;;
            -r|--range)
                start_date="$2"
                end_date="$3"
                shift 3
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            -*)
                echo -e "${RED}Unknown option: $1${NC}"
                show_help
                exit 1
                ;;
            *)
                query="$1"
                shift
                ;;
        esac
    done

    if [ -z "$query" ] && [ -z "$level" ]; then
        echo -e "${RED}Error: Search query or level required${NC}"
        show_help
        exit 1
    fi

    local count=0

    if [ -n "$level" ]; then
        # Search by level
        count=$(search_by_level "$level" "$max_results")
    elif [ -n "$start_date" ] && [ -n "$end_date" ]; then
        # Search by date range
        count=$(search_by_date "$query" "$start_date" "$end_date" "$max_results")
    elif [ -n "$date" ]; then
        # Search by specific date
        count=$(search_by_date "$query" "$date" "$date" "$max_results")
    else
        # Regular search
        count=$(search_in_files "$query" "$max_results" "$case_sensitive")
    fi

    echo ""
    echo -e "${GREEN}Found $count result(s)${NC}"
}

# Run main function
main "$@"

