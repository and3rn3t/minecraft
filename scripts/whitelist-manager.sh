#!/bin/bash
# Whitelist Manager
# Manages Minecraft server whitelist

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
WHITELIST_FILE="${WHITELIST_FILE:-${PROJECT_DIR}/data/whitelist.json}"

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
    # For now, return success
    return 0
}

# Function to add player to whitelist
add_player() {
    local player="$1"

    if [ -z "$player" ]; then
        echo -e "${RED}Error: Player name required${NC}"
        return 1
    fi

    # Validate player name (Minecraft username rules)
    if ! [[ "$player" =~ ^[a-zA-Z0-9_]{3,16}$ ]]; then
        echo -e "${RED}Error: Invalid player name. Must be 3-16 alphanumeric characters or underscores${NC}"
        return 1
    fi

    # Check if already whitelisted
    if is_whitelisted "$player"; then
        echo -e "${YELLOW}Player already whitelisted: $player${NC}"
        return 0
    fi

    # Add via RCON if available
    if check_rcon; then
        send_rcon "whitelist add $player" >/dev/null 2>&1
    fi

    # Add to whitelist.json
    if [ ! -f "$WHITELIST_FILE" ]; then
        echo '[]' > "$WHITELIST_FILE"
    fi

    # Use Python to add player (more reliable JSON handling)
    python3 << EOF
import json
import sys
from datetime import datetime

player_name = "$player"
whitelist_file = "$WHITELIST_FILE"

try:
    with open(whitelist_file, 'r') as f:
        whitelist = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    whitelist = []

# Check if player already exists
if any(p.get('name') == player_name for p in whitelist):
    sys.exit(1)

# Add player
player_entry = {
    "uuid": "",  # UUID will be resolved by server
    "name": player_name
}
whitelist.append(player_entry)

with open(whitelist_file, 'w') as f:
    json.dump(whitelist, f, indent=2)

sys.exit(0)
EOF

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Player added to whitelist: $player${NC}"
        return 0
    else
        echo -e "${RED}✗ Failed to add player to whitelist${NC}"
        return 1
    fi
}

# Function to remove player from whitelist
remove_player() {
    local player="$1"

    if [ -z "$player" ]; then
        echo -e "${RED}Error: Player name required${NC}"
        return 1
    fi

    # Remove via RCON if available
    if check_rcon; then
        send_rcon "whitelist remove $player" >/dev/null 2>&1
    fi

    # Remove from whitelist.json
    if [ ! -f "$WHITELIST_FILE" ]; then
        echo -e "${YELLOW}Whitelist file not found${NC}"
        return 1
    fi

    python3 << EOF
import json
import sys

player_name = "$player"
whitelist_file = "$WHITELIST_FILE"

try:
    with open(whitelist_file, 'r') as f:
        whitelist = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    sys.exit(1)

# Remove player
original_count = len(whitelist)
whitelist = [p for p in whitelist if p.get('name') != player_name]

if len(whitelist) == original_count:
    sys.exit(1)

with open(whitelist_file, 'w') as f:
    json.dump(whitelist, f, indent=2)

sys.exit(0)
EOF

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Player removed from whitelist: $player${NC}"
        return 0
    else
        echo -e "${YELLOW}Player not found in whitelist: $player${NC}"
        return 1
    fi
}

# Function to check if player is whitelisted
is_whitelisted() {
    local player="$1"

    if [ ! -f "$WHITELIST_FILE" ]; then
        return 1
    fi

    python3 << EOF
import json
import sys

player_name = "$player"
whitelist_file = "$WHITELIST_FILE"

try:
    with open(whitelist_file, 'r') as f:
        whitelist = json.load(f)
    if any(p.get('name') == player_name for p in whitelist):
        sys.exit(0)
    else:
        sys.exit(1)
except:
    sys.exit(1)
EOF
}

# Function to list whitelisted players
list_players() {
    if [ ! -f "$WHITELIST_FILE" ]; then
        echo -e "${YELLOW}Whitelist file not found${NC}"
        return 1
    fi

    echo -e "${BLUE}Whitelisted Players:${NC}"
    echo ""

    python3 << EOF
import json

whitelist_file = "$WHITELIST_FILE"

try:
    with open(whitelist_file, 'r') as f:
        whitelist = json.load(f)

    if not whitelist:
        print("  (no players whitelisted)")
    else:
        for player in whitelist:
            name = player.get('name', 'Unknown')
            uuid = player.get('uuid', '')
            if uuid:
                print(f"  - {name} ({uuid})")
            else:
                print(f"  - {name}")

    print(f"\nTotal: {len(whitelist)} player(s)")
except Exception as e:
    print(f"Error reading whitelist: {e}")
EOF
}

# Function to enable whitelist
enable_whitelist() {
    local server_properties="${PROJECT_DIR}/data/server.properties"

    if [ ! -f "$server_properties" ]; then
        echo -e "${RED}Error: server.properties not found${NC}"
        return 1
    fi

    # Update server.properties
    if grep -q "^white-list=" "$server_properties" 2>/dev/null; then
        if [[ "$OSTYPE" == "darwin"* ]]; then
            sed -i '' 's/^white-list=.*/white-list=true/' "$server_properties"
        else
            sed -i 's/^white-list=.*/white-list=true/' "$server_properties"
        fi
    else
        echo "white-list=true" >> "$server_properties"
    fi

    echo -e "${GREEN}✓ Whitelist enabled${NC}"
    echo -e "${YELLOW}Note: Server restart required for changes to take effect${NC}"
}

# Function to disable whitelist
disable_whitelist() {
    local server_properties="${PROJECT_DIR}/data/server.properties"

    if [ ! -f "$server_properties" ]; then
        echo -e "${RED}Error: server.properties not found${NC}"
        return 1
    fi

    # Update server.properties
    if grep -q "^white-list=" "$server_properties" 2>/dev/null; then
        if [[ "$OSTYPE" == "darwin"* ]]; then
            sed -i '' 's/^white-list=.*/white-list=false/' "$server_properties"
        else
            sed -i 's/^white-list=.*/white-list=false/' "$server_properties"
        fi
    else
        echo "white-list=false" >> "$server_properties"
    fi

    echo -e "${GREEN}✓ Whitelist disabled${NC}"
    echo -e "${YELLOW}Note: Server restart required for changes to take effect${NC}"
}

# Function to import whitelist from file
import_whitelist() {
    local import_file="$1"

    if [ -z "$import_file" ] || [ ! -f "$import_file" ]; then
        echo -e "${RED}Error: Import file not found${NC}"
        return 1
    fi

    echo -e "${BLUE}Importing whitelist from: $import_file${NC}"

    # Read player names from file (one per line)
    local count=0
    while IFS= read -r player || [ -n "$player" ]; do
        player=$(echo "$player" | xargs)  # Trim whitespace
        if [ -n "$player" ] && [[ ! "$player" =~ ^# ]]; then
            if add_player "$player"; then
                count=$((count + 1))
            fi
        fi
    done < "$import_file"

    echo -e "${GREEN}✓ Imported $count player(s)${NC}"
}

# Function to export whitelist to file
export_whitelist() {
    local export_file="${1:-whitelist_export_$(date +%Y%m%d_%H%M%S).txt}"

    if [ ! -f "$WHITELIST_FILE" ]; then
        echo -e "${YELLOW}Whitelist file not found${NC}"
        return 1
    fi

    python3 << EOF
import json

whitelist_file = "$WHITELIST_FILE"
export_file = "$export_file"

try:
    with open(whitelist_file, 'r') as f:
        whitelist = json.load(f)

    with open(export_file, 'w') as f:
        for player in whitelist:
            f.write(f"{player.get('name', '')}\n")

    print(f"Exported {len(whitelist)} player(s) to {export_file}")
except Exception as e:
    print(f"Error: {e}")
    exit(1)
EOF

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Whitelist exported to: $export_file${NC}"
    fi
}

# Main function
main() {
    local command="${1:-help}"

    case "$command" in
        add)
            if [ -z "$2" ]; then
                echo -e "${RED}Error: Player name required${NC}"
                exit 1
            fi
            add_player "$2"
            ;;
        remove|rm)
            if [ -z "$2" ]; then
                echo -e "${RED}Error: Player name required${NC}"
                exit 1
            fi
            remove_player "$2"
            ;;
        list|ls)
            list_players
            ;;
        enable|on)
            enable_whitelist
            ;;
        disable|off)
            disable_whitelist
            ;;
        import)
            if [ -z "$2" ]; then
                echo -e "${RED}Error: Import file required${NC}"
                exit 1
            fi
            import_whitelist "$2"
            ;;
        export)
            export_whitelist "$2"
            ;;
        check)
            if [ -z "$2" ]; then
                echo -e "${RED}Error: Player name required${NC}"
                exit 1
            fi
            if is_whitelisted "$2"; then
                echo -e "${GREEN}Player is whitelisted: $2${NC}"
                exit 0
            else
                echo -e "${YELLOW}Player is not whitelisted: $2${NC}"
                exit 1
            fi
            ;;
        help|*)
            echo -e "${BLUE}Whitelist Manager${NC}"
            echo ""
            echo "Usage: $0 {command} [options]"
            echo ""
            echo "Commands:"
            echo "  add <player>        - Add player to whitelist"
            echo "  remove <player>    - Remove player from whitelist"
            echo "  list               - List all whitelisted players"
            echo "  enable             - Enable whitelist in server.properties"
            echo "  disable            - Disable whitelist in server.properties"
            echo "  import <file>      - Import whitelist from file (one player per line)"
            echo "  export [file]      - Export whitelist to file"
            echo "  check <player>     - Check if player is whitelisted"
            echo "  help               - Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0 add PlayerName"
            echo "  $0 remove PlayerName"
            echo "  $0 list"
            echo "  $0 enable"
            echo "  $0 import players.txt"
            echo ""
            exit 1
            ;;
    esac
}

# Run main function
main "$@"

