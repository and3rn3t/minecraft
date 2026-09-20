#!/bin/bash
# OP (Operator) Manager
# Manages Minecraft server operators

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
OPS_FILE="${OPS_FILE:-${PROJECT_DIR}/data/ops.json}"
RCON_CLIENT="${SCRIPT_DIR}/rcon-client.sh"
RCON_CONFIG_FILE="${PROJECT_DIR}/config/rcon.conf"

# Function to check if RCON is available. rcon-client.sh (which actually
# sends the command, over the network — no rcon-cli binary involved) needs
# config/rcon.conf, written by scripts/rcon-setup.sh; checking for that is
# what the rest of this codebase (api/rcon.py) already treats as "RCON is
# configured".
check_rcon() {
    [ -f "$RCON_CONFIG_FILE" ]
}

# Function to send RCON command to the live server. Previously a stub that
# unconditionally returned success without sending anything — grant_op and
# revoke_op only ever edited ops.json on disk, which Minecraft reads once at
# startup, so op/deop never actually took effect for a running server until
# its next restart. Best-effort: a player who's actually online should see
# this apply instantly, but ops.json is what makes it durable, so a failure
# here doesn't abort the caller.
send_rcon() {
    local command="$1"
    "$RCON_CLIENT" command "$command" >/dev/null 2>&1
}

# Function to grant OP to player
grant_op() {
    local player="$1"
    local level="${2:-4}"

    if [ -z "$player" ]; then
        echo -e "${RED}Error: Player name required${NC}"
        return 1
    fi

    # Validate player name
    if ! [[ "$player" =~ ^[a-zA-Z0-9_]{3,16}$ ]]; then
        echo -e "${RED}Error: Invalid player name${NC}"
        return 1
    fi

    # Validate OP level (1-4)
    if ! [[ "$level" =~ ^[1-4]$ ]]; then
        echo -e "${RED}Error: OP level must be between 1 and 4${NC}"
        return 1
    fi

    # Check if already OP
    if is_op "$player"; then
        echo -e "${YELLOW}Player is already an operator: $player${NC}"
        # Update level if different. Best-effort: see the ops.json write
        # below for why this can fail even when nothing is actually wrong.
        update_op_level "$player" "$level" || true
        return 0
    fi

    # Grant OP via RCON if available. A successful RCON "op" is both
    # immediate (an already-connected player sees it live, no reconnect
    # needed) and durable on its own: Minecraft's own RCON handler persists
    # it to ops.json itself, from inside the container, as the container's
    # user. That's exactly why the ops.json write below can't be relied on
    # to always succeed here: once Minecraft — a different UID than this
    # host script runs as — has touched that file, this process may no
    # longer have write access to it (the same class of bind-mount UID
    # mismatch fix-permissions.sh exists for, but recurring: it's not a
    # one-time fix here since Minecraft rewrites the file on every op/deop).
    local rcon_ok=1
    if check_rcon && send_rcon "op $player"; then
        rcon_ok=0
    fi

    # Ensure the file exists before trying to read/write it. Best-effort:
    # if RCON already succeeded, a failure here isn't fatal (see below).
    if [ ! -f "$OPS_FILE" ]; then
        echo '[]' > "$OPS_FILE" 2>/dev/null || true
    fi

    # Only vanilla /op's default level (whatever op-permission-level is in
    # server.properties, normally 4) is guaranteed by RCON alone — it takes
    # no level argument. This write is what applies a non-default level, so
    # it's still attempted even when RCON already succeeded; it's just no
    # longer what decides overall success, per the comment above.
    local write_ok=1
    local write_output
    if write_output=$(python3 2>&1 << EOF
import json
import sys
from datetime import datetime

player_name = "$player"
level = int("$level")
ops_file = "$OPS_FILE"

try:
    with open(ops_file, 'r') as f:
        ops = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    ops = []

# Check if player already OP
if any(p.get('name') == player_name for p in ops):
    # Update level
    for op in ops:
        if op.get('name') == player_name:
            op['level'] = level
            op['bypassesPlayerLimit'] = (level >= 4)
            break
else:
    # Add new OP
    op_entry = {
        "uuid": "",
        "name": player_name,
        "level": level,
        "bypassesPlayerLimit": (level >= 4)
    }
    ops.append(op_entry)

with open(ops_file, 'w') as f:
    json.dump(ops, f, indent=2)

sys.exit(0)
EOF
    ); then
        write_ok=0
    fi

    if [ "$rcon_ok" -eq 0 ] || [ "$write_ok" -eq 0 ]; then
        echo -e "${GREEN}✓ Operator granted: $player (level $level)${NC}"
        if [ "$write_ok" -ne 0 ]; then
            echo -e "${YELLOW}Note: couldn't persist a custom level to ${OPS_FILE} (${write_output}). The RCON grant above still applies, at the server's default op level, and is durable via Minecraft's own write to that file.${NC}" >&2
        fi
        return 0
    else
        echo -e "${RED}✗ Failed to grant operator status: ${write_output}${NC}" >&2
        return 1
    fi
}

# Function to revoke OP from player
revoke_op() {
    local player="$1"

    if [ -z "$player" ]; then
        echo -e "${RED}Error: Player name required${NC}"
        return 1
    fi

    # Revoke OP via RCON if available. See grant_op's matching comment on
    # why this is best-effort and why the ops.json write below can't be
    # relied on either: Minecraft's own RCON "deop" handler already removes
    # the player from that file itself, from inside the container, as the
    # container's user — which is exactly what can leave this host process
    # without write access to it.
    local rcon_ok=1
    if check_rcon && send_rcon "deop $player"; then
        rcon_ok=0
    fi

    local write_ok=1
    local write_output="Ops file not found"
    if [ -f "$OPS_FILE" ]; then
        if write_output=$(python3 2>&1 << EOF
import json
import sys

player_name = "$player"
ops_file = "$OPS_FILE"

try:
    with open(ops_file, 'r') as f:
        ops = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    sys.exit(1)

# Remove player
original_count = len(ops)
ops = [p for p in ops if p.get('name') != player_name]

if len(ops) == original_count:
    print("Player not found in operators list", file=sys.stderr)
    sys.exit(1)

with open(ops_file, 'w') as f:
    json.dump(ops, f, indent=2)

sys.exit(0)
EOF
        ); then
            write_ok=0
        fi
    fi

    if [ "$rcon_ok" -eq 0 ] || [ "$write_ok" -eq 0 ]; then
        echo -e "${GREEN}✓ Operator status revoked: $player${NC}"
        return 0
    else
        echo -e "${YELLOW}${write_output}${NC}"
        return 1
    fi
}

# Function to update OP level
update_op_level() {
    local player="$1"
    local level="$2"

    python3 << EOF
import json
import sys

player_name = "$player"
level = int("$level")
ops_file = "$OPS_FILE"

try:
    with open(ops_file, 'r') as f:
        ops = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    sys.exit(1)

# Update level
for op in ops:
    if op.get('name') == player_name:
        op['level'] = level
        op['bypassesPlayerLimit'] = (level >= 4)
        break
else:
    sys.exit(1)

with open(ops_file, 'w') as f:
    json.dump(ops, f, indent=2)

sys.exit(0)
EOF
}

# Function to check if player is OP
is_op() {
    local player="$1"

    if [ ! -f "$OPS_FILE" ]; then
        return 1
    fi

    python3 << EOF
import json
import sys

player_name = "$player"
ops_file = "$OPS_FILE"

try:
    with open(ops_file, 'r') as f:
        ops = json.load(f)
    if any(p.get('name') == player_name for p in ops):
        sys.exit(0)
    else:
        sys.exit(1)
except:
    sys.exit(1)
EOF
}

# Function to list operators
list_ops() {
    if [ ! -f "$OPS_FILE" ]; then
        echo -e "${YELLOW}Ops file not found${NC}"
        return 1
    fi

    echo -e "${BLUE}Operators:${NC}"
    echo ""

    python3 << EOF
import json

ops_file = "$OPS_FILE"

try:
    with open(ops_file, 'r') as f:
        ops = json.load(f)

    if not ops:
        print("  (no operators)")
    else:
        for op in ops:
            name = op.get('name', 'Unknown')
            level = op.get('level', 4)
            uuid = op.get('uuid', '')
            bypasses = op.get('bypassesPlayerLimit', False)

            if uuid:
                print(f"  - {name} (Level {level}, UUID: {uuid})")
            else:
                print(f"  - {name} (Level {level})")

            if bypasses:
                print(f"    Bypasses player limit: Yes")
            print("")

    print(f"Total: {len(ops)} operator(s)")
except Exception as e:
    print(f"Error reading ops file: {e}")
EOF
}

# Function to get OP level
get_op_level() {
    local player="$1"

    if [ ! -f "$OPS_FILE" ]; then
        return 1
    fi

    python3 << EOF
import json
import sys

player_name = "$player"
ops_file = "$OPS_FILE"

try:
    with open(ops_file, 'r') as f:
        ops = json.load(f)

    for op in ops:
        if op.get('name') == player_name:
            print(op.get('level', 4))
            sys.exit(0)

    sys.exit(1)
except:
    sys.exit(1)
EOF
}

# Main function
main() {
    local command="${1:-help}"

    case "$command" in
        grant|add)
            if [ -z "$2" ]; then
                echo -e "${RED}Error: Player name required${NC}"
                exit 1
            fi
            grant_op "$2" "${3:-4}"
            ;;
        revoke|remove|rm)
            if [ -z "$2" ]; then
                echo -e "${RED}Error: Player name required${NC}"
                exit 1
            fi
            revoke_op "$2"
            ;;
        list|ls)
            list_ops
            ;;
        level)
            if [ -z "$2" ]; then
                echo -e "${RED}Error: Player name required${NC}"
                exit 1
            fi
            local level
            level=$(get_op_level "$2" 2>/dev/null)
            if [ -n "$level" ]; then
                echo "OP Level: $level"
            else
                echo -e "${YELLOW}Player is not an operator${NC}"
                exit 1
            fi
            ;;
        set-level)
            if [ -z "$2" ] || [ -z "$3" ]; then
                echo -e "${RED}Error: Player name and level required${NC}"
                exit 1
            fi
            if ! is_op "$2"; then
                grant_op "$2" "$3"
            else
                update_op_level "$2" "$3"
                echo -e "${GREEN}✓ OP level updated: $2 (level $3)${NC}"
            fi
            ;;
        check)
            if [ -z "$2" ]; then
                echo -e "${RED}Error: Player name required${NC}"
                exit 1
            fi
            if is_op "$2"; then
                local level
                level=$(get_op_level "$2")
                echo -e "${GREEN}Player is an operator: $2 (level $level)${NC}"
                exit 0
            else
                echo -e "${YELLOW}Player is not an operator: $2${NC}"
                exit 1
            fi
            ;;
        help|*)
            echo -e "${BLUE}OP (Operator) Manager${NC}"
            echo ""
            echo "Usage: $0 {command} [options]"
            echo ""
            echo "Commands:"
            echo "  grant <player> [level]  - Grant operator status (level 1-4, default: 4)"
            echo "  revoke <player>         - Revoke operator status"
            echo "  list                    - List all operators"
            echo "  level <player>          - Get operator level"
            echo "  set-level <player> <level> - Set operator level (1-4)"
            echo "  check <player>          - Check if player is operator"
            echo "  help                    - Show this help message"
            echo ""
            echo "OP Levels:"
            echo "  1 - Can use /me, /tell, /list"
            echo "  2 - Level 1 + /give, /clear, /effect, /gamemode"
            echo "  3 - Level 2 + /ban, /kick, /op, /deop"
            echo "  4 - Level 3 + All commands, bypasses player limit"
            echo ""
            echo "Examples:"
            echo "  $0 grant PlayerName 4"
            echo "  $0 revoke PlayerName"
            echo "  $0 set-level PlayerName 2"
            echo "  $0 list"
            echo ""
            exit 1
            ;;
    esac
}

# Run main function
main "$@"
