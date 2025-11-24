#!/bin/bash
# Announcement Manager
# Manages server announcements with scheduling support

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
ANNOUNCEMENTS_FILE="${PROJECT_DIR}/config/announcements.json"
SCRIPTS_DIR="${PROJECT_DIR}/scripts"

# Function to send announcement via RCON
send_announcement() {
    local message="$1"
    local type="${2:-say}"
    local target="${3:-@a}"

    # Escape message for Minecraft
    message=$(echo "$message" | sed 's/"/\\"/g')

    case "$type" in
        say)
            "${SCRIPTS_DIR}/rcon-client.sh" command "say $message"
            ;;
        title)
            "${SCRIPTS_DIR}/rcon-client.sh" command "title $target title {\"text\":\"$message\"}"
            ;;
        subtitle)
            "${SCRIPTS_DIR}/rcon-client.sh" command "title $target subtitle {\"text\":\"$message\"}"
            ;;
        actionbar)
            "${SCRIPTS_DIR}/rcon-client.sh" command "title $target actionbar {\"text\":\"$message\"}"
            ;;
        *)
            "${SCRIPTS_DIR}/rcon-client.sh" command "say $message"
            ;;
    esac
}

# Function to load announcements
load_announcements() {
    if [ ! -f "$ANNOUNCEMENTS_FILE" ]; then
        echo '{"announcements": []}'
        return
    fi

    cat "$ANNOUNCEMENTS_FILE"
}

# Function to save announcements
save_announcements() {
    local data="$1"
    mkdir -p "$(dirname "$ANNOUNCEMENTS_FILE")"
    echo "$data" > "$ANNOUNCEMENTS_FILE"
}

# Function to create announcement
create_announcement() {
    local message="$1"
    local type="${2:-say}"
    local schedule_type="${3:-}"
    local schedule_time="${4:-}"
    local enabled="${5:-true}"

    python3 << EOF
import json
import sys
import uuid
from datetime import datetime
from pathlib import Path

announcements_file = Path("$ANNOUNCEMENTS_FILE")
message = "$message"
announcement_type = "$type"
schedule_type = "$schedule_type"
schedule_time = "$schedule_time"
enabled = "$enabled" == "true"

try:
    # Load existing announcements
    if announcements_file.exists():
        with open(announcements_file, 'r') as f:
            data = json.load(f)
    else:
        data = {"announcements": []}

    # Create new announcement
    announcement = {
        "id": str(uuid.uuid4()),
        "message": message,
        "type": announcement_type,
        "enabled": enabled,
        "created": datetime.now().isoformat(),
    }

    # Add scheduling if provided
    if schedule_type:
        announcement["schedule"] = {
            "type": schedule_type,
            "time": schedule_time,
        }

    data["announcements"].append(announcement)

    # Save
    with open(announcements_file, 'w') as f:
        json.dump(data, f, indent=2)

    print(json.dumps(announcement, indent=2))
except Exception as e:
    print(f"Error: {e}", file=sys.stderr)
    sys.exit(1)
EOF
}

# Function to list announcements
list_announcements() {
    load_announcements | python3 -m json.tool
}

# Function to send announcement by ID
send_by_id() {
    local id="$1"

    python3 << EOF
import json
import sys
from pathlib import Path
import subprocess

announcements_file = Path("$ANNOUNCEMENTS_FILE")
announcement_id = "$id"

try:
    if not announcements_file.exists():
        print("No announcements found", file=sys.stderr)
        sys.exit(1)

    with open(announcements_file, 'r') as f:
        data = json.load(f)

    # Find announcement
    announcement = None
    for ann in data.get("announcements", []):
        if ann.get("id") == announcement_id:
            announcement = ann
            break

    if not announcement:
        print(f"Announcement not found: {announcement_id}", file=sys.stderr)
        sys.exit(1)

    # Send announcement
    message = announcement["message"]
    ann_type = announcement.get("type", "say")

    # Escape message
    message = message.replace('"', '\\"')

    # Build command
    rcon_script = "${SCRIPTS_DIR}/rcon-client.sh"

    if ann_type == "say":
        cmd = f"{rcon_script} command 'say {message}'"
    elif ann_type == "title":
        cmd = f"{rcon_script} command 'title @a title {{\"text\":\"{message}\"}}'"
    elif ann_type == "subtitle":
        cmd = f"{rcon_script} command 'title @a subtitle {{\"text\":\"{message}\"}}'"
    elif ann_type == "actionbar":
        cmd = f"{rcon_script} command 'title @a actionbar {{\"text\":\"{message}\"}}'"
    else:
        cmd = f"{rcon_script} command 'say {message}'"

    # Execute
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

    if result.returncode == 0:
        print(f"Announcement sent: {message}")
    else:
        print(f"Error sending announcement: {result.stderr}", file=sys.stderr)
        sys.exit(1)

except Exception as e:
    print(f"Error: {e}", file=sys.stderr)
    sys.exit(1)
EOF
}

# Function to delete announcement
delete_announcement() {
    local id="$1"

    python3 << EOF
import json
import sys
from pathlib import Path

announcements_file = Path("$ANNOUNCEMENTS_FILE")
announcement_id = "$id"

try:
    if not announcements_file.exists():
        print("No announcements found", file=sys.stderr)
        sys.exit(1)

    with open(announcements_file, 'r') as f:
        data = json.load(f)

    # Remove announcement
    original_count = len(data.get("announcements", []))
    data["announcements"] = [
        ann for ann in data.get("announcements", [])
        if ann.get("id") != announcement_id
    ]

    if len(data["announcements"]) == original_count:
        print(f"Announcement not found: {announcement_id}", file=sys.stderr)
        sys.exit(1)

    # Save
    with open(announcements_file, 'w') as f:
        json.dump(data, f, indent=2)

    print(f"Announcement deleted: {announcement_id}")

except Exception as e:
    print(f"Error: {e}", file=sys.stderr)
    sys.exit(1)
EOF
}

# Main function
main() {
    local command="${1:-help}"

    case "$command" in
        create|add)
            if [ -z "$2" ]; then
                echo -e "${RED}Error: Message required${NC}"
                exit 1
            fi
            create_announcement "$2" "${3:-say}" "${4:-}" "${5:-}" "${6:-true}"
            ;;
        list|ls)
            list_announcements
            ;;
        send)
            if [ -z "$2" ]; then
                echo -e "${RED}Error: Announcement ID required${NC}"
                exit 1
            fi
            send_by_id "$2"
            ;;
        delete|rm)
            if [ -z "$2" ]; then
                echo -e "${RED}Error: Announcement ID required${NC}"
                exit 1
            fi
            delete_announcement "$2"
            ;;
        help|*)
            echo -e "${BLUE}Announcement Manager${NC}"
            echo ""
            echo "Usage: $0 {command} [options]"
            echo ""
            echo "Commands:"
            echo "  create <message> [type] [schedule_type] [schedule_time] [enabled] - Create announcement"
            echo "  list                                                             - List all announcements"
            echo "  send <id>                                                        - Send announcement by ID"
            echo "  delete <id>                                                      - Delete announcement"
            echo "  help                                                             - Show this help message"
            echo ""
            echo "Types: say, title, subtitle, actionbar"
            echo ""
            echo "Examples:"
            echo "  $0 create \"Welcome to our server!\" say"
            echo "  $0 create \"Server restart in 10 minutes\" title daily \"02:50\""
            echo "  $0 send <announcement-id>"
            echo ""
            exit 1
            ;;
    esac
}

# Run main function
main "$@"

