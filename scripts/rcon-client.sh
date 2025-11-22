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
            local result=$(docker exec minecraft-server rcon-cli -H "$RCON_HOST" -p "$RCON_PORT" -P "$RCON_PASSWORD" "$command" 2>&1)
            if [ $? -eq 0 ]; then
                echo "$result"
                return 0
            fi
        fi
    fi

    # Try local rcon-cli
    if command -v rcon-cli >/dev/null 2>&1; then
        local result=$(rcon-cli -H "$RCON_HOST" -p "$RCON_PORT" -P "$RCON_PASSWORD" "$command" 2>&1)
        if [ $? -eq 0 ]; then
            echo "$result"
            return 0
        fi
    fi

    # Fallback: use Python rcon library if available
    if command -v python3 >/dev/null 2>&1; then
        python3 <<EOF
import socket
import struct
import sys

def send_rcon_command(host, port, password, command):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect((host, port))

        # Send authentication
        auth_packet = struct.pack('<iii', 3, 0, len(password) + 2) + password.encode() + b'\x00\x00'
        sock.send(auth_packet)

        # Receive auth response
        response = sock.recv(4096)
        if len(response) < 4:
            print("Authentication failed", file=sys.stderr)
            return 1

        # Send command
        cmd_packet = struct.pack('<iii', 2, 0, len(command) + 2) + command.encode() + b'\x00\x00'
        sock.send(cmd_packet)

        # Receive response
        response = sock.recv(4096)
        if len(response) >= 10:
            response_text = response[10:-2].decode('utf-8', errors='ignore')
            print(response_text)
            return 0
        else:
            print("No response", file=sys.stderr)
            return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    finally:
        sock.close()

sys.exit(send_rcon_command("$RCON_HOST", $RCON_PORT, "$RCON_PASSWORD", "$command"))
EOF
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
    local result=$(send_rcon_command "list" 2>&1)
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
                local result=$(send_rcon_command "$command" 2>&1)
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

