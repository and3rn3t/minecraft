#!/bin/bash
# Mock Minecraft Server
# Provides a mock server for testing without running actual Minecraft server

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
MOCK_SERVER_DIR="${MOCK_SERVER_DIR:-/tmp/mock-minecraft-server}"
MOCK_SERVER_PID="${MOCK_SERVER_PID:-/tmp/mock-minecraft-server.pid}"
MOCK_SERVER_PORT="${MOCK_SERVER_PORT:-25565}"
MOCK_RCON_PORT="${MOCK_RCON_PORT:-25575}"

# Function to start mock server
start_mock_server() {
    if [ -f "$MOCK_SERVER_PID" ]; then
        local pid=$(cat "$MOCK_SERVER_PID")
        if kill -0 "$pid" 2>/dev/null; then
            echo -e "${YELLOW}Mock server already running (PID: $pid)${NC}"
            return 0
        fi
    fi

    mkdir -p "$MOCK_SERVER_DIR"
    echo "Mock Minecraft Server" > "${MOCK_SERVER_DIR}/server.jar"

    # Create mock server process
    (
        while true; do
            sleep 1
            if [ ! -f "$MOCK_SERVER_PID" ]; then
                break
            fi
        done
    ) &

    local pid=$!
    echo "$pid" > "$MOCK_SERVER_PID"

    echo -e "${GREEN}Mock server started (PID: $pid)${NC}"
    echo "Server directory: $MOCK_SERVER_DIR"
}

# Function to stop mock server
stop_mock_server() {
    if [ ! -f "$MOCK_SERVER_PID" ]; then
        echo -e "${YELLOW}Mock server not running${NC}"
        return 0
    fi

    local pid=$(cat "$MOCK_SERVER_PID")
    if kill -0 "$pid" 2>/dev/null; then
        kill "$pid" 2>/dev/null || true
        echo -e "${GREEN}Mock server stopped${NC}"
    else
        echo -e "${YELLOW}Mock server was not running${NC}"
    fi

    rm -f "$MOCK_SERVER_PID"
}

# Function to check mock server status
status_mock_server() {
    if [ ! -f "$MOCK_SERVER_PID" ]; then
        echo "stopped"
        return 1
    fi

    local pid=$(cat "$MOCK_SERVER_PID")
    if kill -0 "$pid" 2>/dev/null; then
        echo "running"
        return 0
    else
        echo "stopped"
        return 1
    fi
}

# Function to send mock RCON command
send_mock_rcon() {
    local command="$1"
    echo "Mock RCON: $command"
    echo "OK"
}

# Function to get mock server logs
get_mock_logs() {
    local log_file="${MOCK_SERVER_DIR}/logs/latest.log"
    if [ -f "$log_file" ]; then
        cat "$log_file"
    else
        echo "[INFO] Mock server log"
    fi
}

# Main function
main() {
    case "${1:-help}" in
        start)
            start_mock_server
            ;;
        stop)
            stop_mock_server
            ;;
        status)
            status_mock_server
            ;;
        restart)
            stop_mock_server
            sleep 1
            start_mock_server
            ;;
        help|*)
            echo "Mock Minecraft Server"
            echo ""
            echo "Usage: $0 {start|stop|status|restart|help}"
            echo ""
            echo "Commands:"
            echo "  start   - Start mock server"
            echo "  stop    - Stop mock server"
            echo "  status  - Check server status"
            echo "  restart - Restart mock server"
            echo ""
            exit 1
            ;;
    esac
}

# Run main function
main "$@"

