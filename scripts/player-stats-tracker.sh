#!/bin/bash
# Player Statistics Tracker
# Tracks player statistics from server logs and commands

set -e

# Colors for output
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
STATS_DIR="${PROJECT_DIR}/data/stats"
STATS_FILE="${STATS_DIR}/player-stats.json"
LOG_FILE="${PROJECT_DIR}/data/logs/latest.log"

# Ensure stats directory exists
mkdir -p "$STATS_DIR"

# Function to initialize stats file
init_stats_file() {
    if [ ! -f "$STATS_FILE" ]; then
        echo '{}' > "$STATS_FILE"
    fi
}

# Function to get player stats
get_player_stats() {
    local player="$1"
    init_stats_file

    python3 << EOF
import json
import sys
from pathlib import Path

stats_file = Path("$STATS_FILE")
player = "$player"

try:
    with open(stats_file, 'r') as f:
        stats = json.load(f)

    player_stats = stats.get(player, {})
    print(json.dumps(player_stats, indent=2))
except Exception as e:
    print(f"Error: {e}", file=sys.stderr)
    sys.exit(1)
EOF
}

# Function to update player stats
update_player_stat() {
    local player="$1"
    local stat_key="$2"
    local stat_value="$3"
    init_stats_file

    python3 << EOF
import json
import sys
from pathlib import Path
from datetime import datetime

stats_file = Path("$STATS_FILE")
player = "$player"
stat_key = "$stat_key"
stat_value = "$stat_value"

try:
    with open(stats_file, 'r') as f:
        stats = json.load(f)

    if player not in stats:
        stats[player] = {
            "first_seen": datetime.now().isoformat(),
            "last_seen": datetime.now().isoformat(),
            "play_time_minutes": 0,
            "login_count": 0,
            "logout_count": 0,
            "deaths": 0,
            "blocks_broken": 0,
            "blocks_placed": 0,
        }

    # Update stat
    if stat_key == "login":
        stats[player]["login_count"] = stats[player].get("login_count", 0) + 1
        stats[player]["last_seen"] = datetime.now().isoformat()
    elif stat_key == "logout":
        stats[player]["logout_count"] = stats[player].get("logout_count", 0) + 1
        # Calculate session time if we have login timestamp
        # This is simplified - in production you'd track session start
    elif stat_key == "death":
        stats[player]["deaths"] = stats[player].get("deaths", 0) + 1
    elif stat_key in ["blocks_broken", "blocks_placed"]:
        stats[player][stat_key] = stats[player].get(stat_key, 0) + int(stat_value or 1)
    else:
        stats[player][stat_key] = stat_value

    with open(stats_file, 'w') as f:
        json.dump(stats, f, indent=2)

    print("OK")
except Exception as e:
    print(f"Error: {e}", file=sys.stderr)
    sys.exit(1)
EOF
}

# Function to parse log for player events
parse_logs() {
    if [ ! -f "$LOG_FILE" ]; then
        echo -e "${YELLOW}Log file not found: $LOG_FILE${NC}"
        return 1
    fi

    python3 << EOF
import json
import re
from pathlib import Path
from datetime import datetime

log_file = Path("$LOG_FILE")
stats_file = Path("$STATS_FILE")

# Load existing stats
if stats_file.exists():
    with open(stats_file, 'r') as f:
        stats = json.load(f)
else:
    stats = {}

# Parse log for player events
login_pattern = re.compile(r'(\[.*?\]) \[.*?\]: (\w+) joined the game')
logout_pattern = re.compile(r'(\[.*?\]) \[.*?\]: (\w+) left the game')
death_pattern = re.compile(r'(\[.*?\]) \[.*?\]: (\w+) (was|died|blew up|fell|drowned|etc)')

try:
    with open(log_file, 'r') as f:
        for line in f:
            # Check for login
            match = login_pattern.search(line)
            if match:
                player = match.group(2)
                if player not in stats:
                    stats[player] = {
                        "first_seen": datetime.now().isoformat(),
                        "login_count": 0,
                        "logout_count": 0,
                        "deaths": 0,
                    }
                stats[player]["login_count"] = stats[player].get("login_count", 0) + 1
                stats[player]["last_seen"] = datetime.now().isoformat()

            # Check for logout
            match = logout_pattern.search(line)
            if match:
                player = match.group(2)
                if player not in stats:
                    stats[player] = {"logout_count": 0}
                stats[player]["logout_count"] = stats[player].get("logout_count", 0) + 1

            # Check for death (simplified pattern)
            match = death_pattern.search(line)
            if match:
                player = match.group(2)
                if player not in stats:
                    stats[player] = {"deaths": 0}
                stats[player]["deaths"] = stats[player].get("deaths", 0) + 1

    # Save stats
    with open(stats_file, 'w') as f:
        json.dump(stats, f, indent=2)

    print("Log parsed successfully")
except Exception as e:
    print(f"Error parsing log: {e}", file=sys.stderr)
    sys.exit(1)
EOF
}

# Function to list all player stats
list_all_stats() {
    init_stats_file

    python3 << EOF
import json
from pathlib import Path

stats_file = Path("$STATS_FILE")

try:
    with open(stats_file, 'r') as f:
        stats = json.load(f)

    print(json.dumps(stats, indent=2))
except Exception as e:
    print(f"Error: {e}", file=sys.stderr)
    sys.exit(1)
EOF
}

# Function to get leaderboard
get_leaderboard() {
    local metric="$1"
    local limit="${2:-10}"
    init_stats_file

    python3 << EOF
import json
from pathlib import Path

stats_file = Path("$STATS_FILE")
metric = "$metric"
limit = int("$limit")

try:
    with open(stats_file, 'r') as f:
        stats = json.load(f)

    # Sort by metric
    players = []
    for player, data in stats.items():
        value = data.get(metric, 0)
        players.append({"player": player, metric: value})

    players.sort(key=lambda x: x.get(metric, 0), reverse=True)

    # Print top N
    result = {"leaderboard": players[:limit], "metric": metric}
    print(json.dumps(result, indent=2))
except Exception as e:
    print(f"Error: {e}", file=sys.stderr)
    sys.exit(1)
EOF
}

# Main function
main() {
    local command="${1:-help}"

    case "$command" in
        get)
            if [ -z "$2" ]; then
                echo -e "${RED}Error: Player name required${NC}"
                exit 1
            fi
            get_player_stats "$2"
            ;;
        update)
            if [ -z "$2" ] || [ -z "$3" ]; then
                echo -e "${RED}Error: Player name and stat key required${NC}"
                exit 1
            fi
            update_player_stat "$2" "$3" "$4"
            ;;
        parse)
            parse_logs
            ;;
        list)
            list_all_stats
            ;;
        leaderboard|top)
            get_leaderboard "${2:-login_count}" "${3:-10}"
            ;;
        help|*)
            echo -e "${BLUE}Player Statistics Tracker${NC}"
            echo ""
            echo "Usage: $0 {command} [options]"
            echo ""
            echo "Commands:"
            echo "  get <player>              - Get player statistics"
            echo "  update <player> <key> [value] - Update player stat"
            echo "  parse                     - Parse server logs for player events"
            echo "  list                      - List all player statistics"
            echo "  leaderboard [metric] [limit] - Get leaderboard"
            echo "  help                      - Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0 get PlayerName"
            echo "  $0 update PlayerName login"
            echo "  $0 update PlayerName blocks_broken 10"
            echo "  $0 leaderboard login_count 10"
            echo ""
            exit 1
            ;;
    esac
}

# Run main function
main "$@"

