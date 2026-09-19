#!/bin/bash
# Ban Manager
# Manages Minecraft server bans

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
BANNED_PLAYERS_FILE="${BANNED_PLAYERS_FILE:-${PROJECT_DIR}/data/banned-players.json}"
BANNED_IPS_FILE="${BANNED_IPS_FILE:-${PROJECT_DIR}/data/banned-ips.json}"

# Function to check if RCON is available
check_rcon() {
    if ! command -v rcon-cli >/dev/null 2>&1; then
        return 1
    fi
    return 0
}

# Function to send RCON command
send_rcon() {
    local command="$1"
    # This would use rcon-cli or manage.sh rcon
    return 0
}

# Function to ban player
ban_player() {
    local player="$1"
    local reason="${2:-Banned by operator}"
    local expires="${3:-}"

    if [ -z "$player" ]; then
        echo -e "${RED}Error: Player name required${NC}"
        return 1
    fi

    # Validate player name
    if ! [[ "$player" =~ ^[a-zA-Z0-9_]{3,16}$ ]]; then
        echo -e "${RED}Error: Invalid player name${NC}"
        return 1
    fi

    # Check if already banned
    if is_banned "$player"; then
        echo -e "${YELLOW}Player already banned: $player${NC}"
        return 0
    fi

    # Ban via RCON if available
    if check_rcon; then
        if [ -n "$expires" ]; then
            send_rcon "ban $player $reason" >/dev/null 2>&1
        else
            send_rcon "ban $player $reason" >/dev/null 2>&1
        fi
    fi

    # Add to banned-players.json
    if [ ! -f "$BANNED_PLAYERS_FILE" ]; then
        echo '[]' > "$BANNED_PLAYERS_FILE"
    fi

    python3 << EOF
import json
import sys
from datetime import datetime

player_name = "$player"
reason = "$reason"
expires_str = "$expires"
banned_file = "$BANNED_PLAYERS_FILE"

try:
    with open(banned_file, 'r') as f:
        banned = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    banned = []

# Check if player already banned
if any(p.get('name') == player_name for p in banned):
    sys.exit(1)

# Create ban entry
ban_entry = {
    "uuid": "",
    "name": player_name,
    "created": datetime.now().strftime("%Y-%m-%d %H:%M:%S +0000"),
    "source": "Server",
    "expires": expires_str if expires_str else "forever",
    "reason": reason
}
banned.append(ban_entry)

with open(banned_file, 'w') as f:
    json.dump(banned, f, indent=2)

sys.exit(0)
EOF

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Player banned: $player${NC}"
        echo "  Reason: $reason"
        if [ -n "$expires" ]; then
            echo "  Expires: $expires"
        fi
        return 0
    else
        echo -e "${RED}✗ Failed to ban player${NC}"
        return 1
    fi
}

# Function to unban player
unban_player() {
    local player="$1"

    if [ -z "$player" ]; then
        echo -e "${RED}Error: Player name required${NC}"
        return 1
    fi

    # Unban via RCON if available
    if check_rcon; then
        send_rcon "pardon $player" >/dev/null 2>&1
    fi

    # Remove from banned-players.json
    if [ ! -f "$BANNED_PLAYERS_FILE" ]; then
        echo -e "${YELLOW}Ban file not found${NC}"
        return 1
    fi

    python3 << EOF
import json
import sys

player_name = "$player"
banned_file = "$BANNED_PLAYERS_FILE"

try:
    with open(banned_file, 'r') as f:
        banned = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    sys.exit(1)

# Remove player
original_count = len(banned)
banned = [p for p in banned if p.get('name') != player_name]

if len(banned) == original_count:
    sys.exit(1)

with open(banned_file, 'w') as f:
    json.dump(banned, f, indent=2)

sys.exit(0)
EOF

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Player unbanned: $player${NC}"
        return 0
    else
        echo -e "${YELLOW}Player not found in ban list: $player${NC}"
        return 1
    fi
}

# Function to check if player is banned
is_banned() {
    local player="$1"

    if [ ! -f "$BANNED_PLAYERS_FILE" ]; then
        return 1
    fi

    python3 << EOF
import json
import sys

player_name = "$player"
banned_file = "$BANNED_PLAYERS_FILE"

try:
    with open(banned_file, 'r') as f:
        banned = json.load(f)
    if any(p.get('name') == player_name for p in banned):
        sys.exit(0)
    else:
        sys.exit(1)
except:
    sys.exit(1)
EOF
}

# Function to list banned players
list_banned() {
    if [ ! -f "$BANNED_PLAYERS_FILE" ]; then
        echo -e "${YELLOW}Ban file not found${NC}"
        return 1
    fi

    echo -e "${BLUE}Banned Players:${NC}"
    echo ""

    python3 << EOF
import json
from datetime import datetime

banned_file = "$BANNED_PLAYERS_FILE"

try:
    with open(banned_file, 'r') as f:
        banned = json.load(f)

    if not banned:
        print("  (no players banned)")
    else:
        for ban in banned:
            name = ban.get('name', 'Unknown')
            reason = ban.get('reason', 'No reason')
            created = ban.get('created', 'Unknown')
            expires = ban.get('expires', 'forever')

            print(f"  - {name}")
            print(f"    Reason: {reason}")
            print(f"    Banned: {created}")
            print(f"    Expires: {expires}")
            print("")

    print(f"Total: {len(banned)} player(s)")
except Exception as e:
    print(f"Error reading ban list: {e}")
EOF
}

# Function to ban IP address
ban_ip() {
    local ip="$1"
    local reason="${2:-Banned by operator}"

    if [ -z "$ip" ]; then
        echo -e "${RED}Error: IP address required${NC}"
        return 1
    fi

    # Validate IP address (basic)
    if ! [[ "$ip" =~ ^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$ ]]; then
        echo -e "${RED}Error: Invalid IP address format${NC}"
        return 1
    fi

    # Ban IP via RCON if available
    if check_rcon; then
        send_rcon "ban-ip $ip" >/dev/null 2>&1
    fi

    # Add to banned-ips.json
    if [ ! -f "$BANNED_IPS_FILE" ]; then
        echo '[]' > "$BANNED_IPS_FILE"
    fi

    python3 << EOF
import json
from datetime import datetime

ip_address = "$ip"
reason = "$reason"
banned_file = "$BANNED_IPS_FILE"

try:
    with open(banned_file, 'r') as f:
        banned = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    banned = []

# Check if IP already banned
if any(b.get('ip') == ip_address for b in banned):
    sys.exit(1)

# Create ban entry
ban_entry = {
    "ip": ip_address,
    "created": datetime.now().strftime("%Y-%m-%d %H:%M:%S +0000"),
    "source": "Server",
    "expires": "forever",
    "reason": reason
}
banned.append(ban_entry)

with open(banned_file, 'w') as f:
    json.dump(banned, f, indent=2)

sys.exit(0)
EOF

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ IP address banned: $ip${NC}"
        return 0
    else
        echo -e "${RED}✗ Failed to ban IP address${NC}"
        return 1
    fi
}

# Function to unban IP address
unban_ip() {
    local ip="$1"

    if [ -z "$ip" ]; then
        echo -e "${RED}Error: IP address required${NC}"
        return 1
    fi

    # Unban IP via RCON if available
    if check_rcon; then
        send_rcon "pardon-ip $ip" >/dev/null 2>&1
    fi

    # Remove from banned-ips.json
    if [ ! -f "$BANNED_IPS_FILE" ]; then
        echo -e "${YELLOW}Ban file not found${NC}"
        return 1
    fi

    python3 << EOF
import json
import sys

ip_address = "$ip"
banned_file = "$BANNED_IPS_FILE"

try:
    with open(banned_file, 'r') as f:
        banned = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    sys.exit(1)

# Remove IP
original_count = len(banned)
banned = [b for b in banned if b.get('ip') != ip_address]

if len(banned) == original_count:
    sys.exit(1)

with open(banned_file, 'w') as f:
    json.dump(banned, f, indent=2)

sys.exit(0)
EOF

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ IP address unbanned: $ip${NC}"
        return 0
    else
        echo -e "${YELLOW}IP address not found in ban list: $ip${NC}"
        return 1
    fi
}

# Main function
main() {
    local command="${1:-help}"

    case "$command" in
        ban)
            if [ -z "$2" ]; then
                echo -e "${RED}Error: Player name required${NC}"
                exit 1
            fi
            ban_player "$2" "$3" "$4"
            ;;
        unban|pardon)
            if [ -z "$2" ]; then
                echo -e "${RED}Error: Player name required${NC}"
                exit 1
            fi
            unban_player "$2"
            ;;
        ban-ip)
            if [ -z "$2" ]; then
                echo -e "${RED}Error: IP address required${NC}"
                exit 1
            fi
            ban_ip "$2" "$3"
            ;;
        unban-ip|pardon-ip)
            if [ -z "$2" ]; then
                echo -e "${RED}Error: IP address required${NC}"
                exit 1
            fi
            unban_ip "$2"
            ;;
        list)
            list_banned
            ;;
        check)
            if [ -z "$2" ]; then
                echo -e "${RED}Error: Player name required${NC}"
                exit 1
            fi
            if is_banned "$2"; then
                echo -e "${RED}Player is banned: $2${NC}"
                exit 0
            else
                echo -e "${GREEN}Player is not banned: $2${NC}"
                exit 1
            fi
            ;;
        help|*)
            echo -e "${BLUE}Ban Manager${NC}"
            echo ""
            echo "Usage: $0 {command} [options]"
            echo ""
            echo "Commands:"
            echo "  ban <player> [reason]     - Ban player"
            echo "  unban <player>            - Unban player"
            echo "  ban-ip <ip> [reason]      - Ban IP address"
            echo "  unban-ip <ip>             - Unban IP address"
            echo "  list                      - List all banned players"
            echo "  check <player>            - Check if player is banned"
            echo "  help                      - Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0 ban PlayerName \"Griefing\""
            echo "  $0 unban PlayerName"
            echo "  $0 ban-ip 192.168.1.100 \"Suspicious activity\""
            echo "  $0 list"
            echo ""
            exit 1
            ;;
    esac
}

# Run main function
main "$@"

