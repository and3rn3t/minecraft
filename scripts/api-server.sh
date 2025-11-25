#!/bin/bash
# API Server Management Script
# Manages the REST API server for Minecraft server

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
API_DIR="${PROJECT_DIR}/api"
API_CONFIG="${PROJECT_DIR}/config/api.conf"
API_KEYS_FILE="${PROJECT_DIR}/config/api-keys.json"
PID_FILE="${PROJECT_DIR}/api/api-server.pid"

# Function to check if Python is available
check_python() {
    if command -v python3 >/dev/null 2>&1; then
        return 0
    elif command -v python >/dev/null 2>&1; then
        return 0
    else
        echo -e "${RED}Error: Python 3 not found${NC}"
        echo -e "${YELLOW}Install Python 3 to use the API server${NC}"
        return 1
    fi
}

# Function to install dependencies
install_dependencies() {
    echo -e "${BLUE}Installing API dependencies...${NC}"

    if [ -f "${API_DIR}/requirements.txt" ]; then
        python3 -m pip install --user -r "${API_DIR}/requirements.txt" 2>/dev/null || {
            echo -e "${YELLOW}Warning: Failed to install dependencies${NC}"
            echo -e "${YELLOW}Try: pip3 install -r ${API_DIR}/requirements.txt${NC}"
        }
    fi
}

# Function to start API server
start_api() {
    if [ -f "$PID_FILE" ]; then
        local pid=$(cat "$PID_FILE" 2>/dev/null)
        if ps -p "$pid" > /dev/null 2>&1; then
            echo -e "${YELLOW}API server is already running (PID: $pid)${NC}"
            return 0
        fi
        rm -f "$PID_FILE"
    fi

    if ! check_python; then
        return 1
    fi

    # Check for virtual environment
    VENV_PYTHON=""
    if [ -d "${API_DIR}/venv" ] && [ -f "${API_DIR}/venv/bin/python" ]; then
        VENV_PYTHON="${API_DIR}/venv/bin/python"
        echo -e "${BLUE}Using virtual environment${NC}"

        # Check if dependencies are installed in venv
        if ! "$VENV_PYTHON" -c "import flask" 2>/dev/null; then
            echo -e "${YELLOW}Dependencies not installed in venv, installing...${NC}"
            "$VENV_PYTHON" -m pip install -r "${API_DIR}/requirements.txt" || {
                echo -e "${RED}Failed to install dependencies${NC}"
                return 1
            }
        fi
    else
        echo -e "${YELLOW}Virtual environment not found, using system Python${NC}"
        echo -e "${YELLOW}Consider running: ./scripts/setup-api-venv.sh${NC}"

        # Install dependencies if needed
        if ! python3 -c "import flask" 2>/dev/null; then
            install_dependencies
        fi
        VENV_PYTHON="python3"
    fi

    echo -e "${BLUE}Starting API server...${NC}"

    # Start API server in background
    cd "$API_DIR"
    nohup "$VENV_PYTHON" server.py > "${PROJECT_DIR}/logs/api-server.log" 2>&1 &
    local pid=$!
    echo $pid > "$PID_FILE"

    sleep 2

    if ps -p "$pid" > /dev/null 2>&1; then
        echo -e "${GREEN}API server started (PID: $pid)${NC}"

        # Get port from config
        local port=8080
        if [ -f "$API_CONFIG" ]; then
            port=$(grep "^API_PORT=" "$API_CONFIG" 2>/dev/null | cut -d'=' -f2 || echo "8080")
        fi

        echo -e "${BLUE}API available at: http://localhost:$port/api${NC}"
    else
        echo -e "${RED}Failed to start API server${NC}"
        echo -e "${YELLOW}Check logs: ${PROJECT_DIR}/logs/api-server.log${NC}"
        rm -f "$PID_FILE"
        return 1
    fi
}

# Function to stop API server
stop_api() {
    if [ ! -f "$PID_FILE" ]; then
        echo -e "${YELLOW}API server is not running${NC}"
        return 0
    fi

    local pid=$(cat "$PID_FILE" 2>/dev/null)

    if [ -z "$pid" ] || ! ps -p "$pid" > /dev/null 2>&1; then
        echo -e "${YELLOW}API server is not running${NC}"
        rm -f "$PID_FILE"
        return 0
    fi

    echo -e "${BLUE}Stopping API server (PID: $pid)...${NC}"
    kill "$pid" 2>/dev/null || true

    sleep 2

    if ps -p "$pid" > /dev/null 2>&1; then
        echo -e "${YELLOW}Force killing API server...${NC}"
        kill -9 "$pid" 2>/dev/null || true
    fi

    rm -f "$PID_FILE"
    echo -e "${GREEN}API server stopped${NC}"
}

# Function to restart API server
restart_api() {
    stop_api
    sleep 1
    start_api
}

# Function to check API status
status_api() {
    if [ -f "$PID_FILE" ]; then
        local pid=$(cat "$PID_FILE" 2>/dev/null)
        if ps -p "$pid" > /dev/null 2>&1; then
            echo -e "${GREEN}API server is running (PID: $pid)${NC}"

            # Get port from config
            local port=8080
            if [ -f "$API_CONFIG" ]; then
                port=$(grep "^API_PORT=" "$API_CONFIG" 2>/dev/null | cut -d'=' -f2 || echo "8080")
            fi

            echo -e "${BLUE}API URL: http://localhost:$port/api${NC}"
            return 0
        else
            echo -e "${RED}API server is not running (stale PID file)${NC}"
            rm -f "$PID_FILE"
            return 1
        fi
    else
        echo -e "${RED}API server is not running${NC}"
        return 1
    fi
}

# Function to show API logs
logs_api() {
    local log_file="${PROJECT_DIR}/logs/api-server.log"

    if [ -f "$log_file" ]; then
        tail -f "$log_file"
    else
        echo -e "${YELLOW}No log file found${NC}"
    fi
}

# Function to display usage
usage() {
    echo -e "${BLUE}API Server Management${NC}"
    echo ""
    echo "Usage: $0 {start|stop|restart|status|logs|install-deps}"
    echo ""
    echo "Commands:"
    echo "  start        - Start the API server"
    echo "  stop         - Stop the API server"
    echo "  restart      - Restart the API server"
    echo "  status       - Check API server status"
    echo "  logs         - View API server logs"
    echo "  install-deps - Install Python dependencies"
    echo ""
    exit 1
}

# Main function
main() {
    case "${1:-}" in
        start)
            start_api
            ;;
        stop)
            stop_api
            ;;
        restart)
            restart_api
            ;;
        status)
            status_api
            ;;
        logs)
            logs_api
            ;;
        install-deps)
            install_dependencies
            ;;
        *)
            usage
            ;;
    esac
}

# Run main function
main "$@"

