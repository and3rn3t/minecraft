#!/bin/bash
# RCON Client for Minecraft Server
# Provides command-line interface to send commands via RCON

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
RCON_CONFIG="${PROJECT_DIR}/config/rcon.conf"

# Default RCON settings
RCON_HOST="localhost"
RCON_PORT=25575
RCON_PASSWORD=""

# Load configuration if it exists
if [ -f "$RCON_CONFIG" ]; then
    source "$RCON_CONFIG"
fi

# Function to check if RCON is available
check_rcon_available() {
    # Check if rcon-cli is available in container
    if docker ps | grep -q minecraft-server; then
        if docker exec minecraft-server command -v rcon-cli >/dev/null 2>&1; then
            return 0
        fi
    fi

    # Check if rcon-cli is available locally
    if command -v rcon-cli >/dev/null 2>&1; then
        return 0
    fi

    return 1
}

# Function to send RCON command
send_rcon_command() {
    local command="$1"

    if [ -z "$command" ]; then
        echo -e "${RED}Error: Command not specified${NC}"
        return 1
    fi

    if [ -z "$RCON_PASSWORD" ]; then
        echo -e "${RED}Error: RCON password not configured${NC}"
        echo -e "${YELLOW}Run: $0 setup${NC}"
        return 1
    fi

    # Try to use rcon-cli from container first
    if docker ps | grep -q minecraft-server; then
        if docker exec minecraft-server command -v rcon-cli >/dev/null 2>&1; then
            local result
            result=$(docker exec minecraft-server rcon-cli -H "$RCON_HOST" -p "$RCON_PORT" -P "$RCON_PASSWORD" "$command" 2>&1)
            if [ $? -eq 0 ]; then
                echo "$result"
                return 0
            fi
        fi
    fi

    # Try local rcon-cli
    if command -v rcon-cli >/dev/null 2>&1; then
        local result
        result=$(rcon-cli -H "$RCON_HOST" -p "$RCON_PORT" -P "$RCON_PASSWORD" "$command" 2>&1)
        if [ $? -eq 0 ]; then
            echo "$result"
            return 0
        fi
    fi

    # Fallback: api/rcon.py, over a fresh connection (this script is a
    # one-shot CLI invocation, not the long-lived API process, so it can't
    # share that module's persistent connection). It reads config/rcon.conf
    # itself -- the same file this script already sourced above -- so
    # nothing needs passing through.
    #
    # This used to be a Python heredoc reimplementing the RCON wire protocol
    # inline, with two real bugs: no length-prefix framing on the packets it
    # sent, and an auth-failure check that only tripped on a suspiciously
    # short reply instead of checking the protocol's own -1 request id (so
    # it could report "Authentication failed" for reasons that had nothing
    # to do with authentication -- exactly what a malformed, unframed packet
    # would provoke). api/rcon.py's own docstring documents this same class
    # of bug in this script's *previous* approach; shelling out to it
    # instead of maintaining a second implementation is the fix.
    if command -v python3 >/dev/null 2>&1; then
        python3 "${PROJECT_DIR}/api/rcon.py" "$command"
        return $?
    fi

    echo -e "${RED}Error: RCON client not available${NC}"
    echo -e "${YELLOW}Install rcon-cli or enable RCON in server${NC}"
    return 1
}

# Function to test RCON connection
test_rcon() {
    echo -e "${BLUE}Testing RCON connection...${NC}"

    if [ -z "$RCON_PASSWORD" ]; then
        echo -e "${RED}Error: RCON password not configured${NC}"
        return 1
    fi

    # Test with list command
    local result
    result=$(send_rcon_command "list" 2>&1)
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}RCON connection successful${NC}"
        echo "Response: $result"
        return 0
    else
        echo -e "${RED}RCON connection failed${NC}"
        echo "Error: $result"
        return 1
    fi
}

# Function to interactive RCON session
interactive_rcon() {
    echo -e "${BLUE}RCON Interactive Session${NC}"
    echo -e "${YELLOW}Type 'exit' or 'quit' to end session${NC}"
    echo ""

    while true; do
        read -p "RCON> " command
        if [ -z "$command" ]; then
            continue
        fi

        case "$command" in
            exit|quit|q)
                echo -e "${GREEN}Exiting RCON session${NC}"
                break
                ;;
            *)
                local result
                result=$(send_rcon_command "$command" 2>&1)
                if [ $? -eq 0 ]; then
                    echo "$result"
                else
                    echo -e "${RED}Error: $result${NC}"
                fi
                ;;
        esac
    done
}

# Function to display usage
usage() {
    echo -e "${BLUE}RCON Client for Minecraft Server${NC}"
    echo ""
    echo "Usage: $0 {command|test|interactive|setup} [options]"
    echo ""
    echo "Commands:"
    echo "  command <cmd>     - Send a single RCON command"
    echo "  test              - Test RCON connection"
    echo "  interactive       - Start interactive RCON session"
    echo "  setup             - Configure RCON settings"
    echo ""
    echo "Examples:"
    echo "  $0 command \"list\""
    echo "  $0 command \"say Hello World\""
    echo "  $0 command \"whitelist add PlayerName\""
    echo "  $0 test"
    echo "  $0 interactive"
    echo ""
    exit 1
}

# Main function
main() {
    case "${1:-}" in
        command)
            if [ -z "$2" ]; then
                echo -e "${RED}Error: Command not specified${NC}"
                usage
            fi
            send_rcon_command "$2"
            ;;
        test)
            test_rcon
            ;;
        interactive)
            interactive_rcon
            ;;
        setup)
            echo -e "${BLUE}RCON Configuration Setup${NC}"
            echo ""
            read -p "RCON Host [localhost]: " host
            host=${host:-localhost}
            read -p "RCON Port [25575]: " port
            port=${port:-25575}
            read -sp "RCON Password: " password
            echo ""

            mkdir -p "$(dirname "$RCON_CONFIG")"
            cat > "$RCON_CONFIG" <<EOF
# RCON Configuration
RCON_HOST=$host
RCON_PORT=$port
RCON_PASSWORD=$password
EOF
            chmod 600 "$RCON_CONFIG"
            echo -e "${GREEN}RCON configuration saved${NC}"
            ;;
        *)
            usage
            ;;
    esac
}

# Run main function
main "$@"
