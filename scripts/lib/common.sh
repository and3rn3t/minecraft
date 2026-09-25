#!/bin/bash
# Shared helpers for the management scripts.
#
# Source it from a script in scripts/:
#     # shellcheck source=lib/common.sh
#     source "$(dirname "${BASH_SOURCE[0]}")/lib/common.sh"

# Guard against being sourced twice
if [ -n "${MINECRAFT_COMMON_SH_LOADED:-}" ]; then
    return 0
fi
MINECRAFT_COMMON_SH_LOADED=1

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color
export RED GREEN YELLOW BLUE NC

# Repository layout. BASH_SOURCE[0] is this file, which lives in scripts/lib/.
COMMON_LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPTS_DIR="$(dirname "$COMMON_LIB_DIR")"
PROJECT_DIR="$(dirname "$SCRIPTS_DIR")"
export SCRIPTS_DIR PROJECT_DIR

# Resolve the Docker Compose command once.
# Compose v1 (the `docker-compose` binary) reached end of life in July 2023;
# prefer the v2 plugin and fall back only if the plugin is absent.
_COMPOSE_CMD=""
compose() {
    if [ -z "$_COMPOSE_CMD" ]; then
        if docker compose version >/dev/null 2>&1; then
            _COMPOSE_CMD="docker compose"
        elif command -v docker-compose >/dev/null 2>&1; then
            _COMPOSE_CMD="docker-compose"
        else
            echo -e "${RED}Neither 'docker compose' nor 'docker-compose' is available${NC}" >&2
            return 127
        fi
    fi

    # Word splitting is intended here: the command is one or two words
    # shellcheck disable=SC2086
    $_COMPOSE_CMD "$@"
}

# Print the resolved compose command, for messages and scripts that need it
compose_cmd() {
    compose version >/dev/null 2>&1 || return 127
    echo "$_COMPOSE_CMD"
}

log_info()    { echo -e "${BLUE}$*${NC}"; }
log_success() { echo -e "${GREEN}$*${NC}"; }
log_warn()    { echo -e "${YELLOW}$*${NC}" >&2; }
log_error()   { echo -e "${RED}$*${NC}" >&2; }

# True when the named container is running
container_running() {
    local name="${1:-minecraft-server}"
    docker ps --format '{{.Names}}' 2>/dev/null | grep -qx "$name"
}

# Take the lock that serialises everything that changes the running server:
# scripts/deploy-agent.sh and scripts/auto-update.sh both hold it, so one never
# pulls, rebuilds or recreates the container while the other is mid-way.
# Held on fd 9 until the calling script exits. Fails when it is already held.
take_update_lock() {
    mkdir -p "${PROJECT_DIR}/.deploy"
    exec 9>"${PROJECT_DIR}/.deploy/lock"
    flock -n 9
}

# Print how many players are online. Fails when the server does not answer,
# which callers should treat as "unknown", not as "empty". PLAYER_COUNT_CMD
# replaces the probe, for tests.
players_online() {
    if [ -n "${PLAYER_COUNT_CMD:-}" ]; then
        # Word splitting is intended: the override is a command line
        # shellcheck disable=SC2086
        $PLAYER_COUNT_CMD
        return
    fi
    # A custom game port lives in .env, which systemd units do not load
    local port="${SERVER_PORT:-}"
    if [ -z "$port" ] && [ -f "${PROJECT_DIR}/.env" ]; then
        port="$(sed -n 's/^SERVER_PORT=//p' "${PROJECT_DIR}/.env" | tail -1)"
    fi
    SERVER_PORT="${port:-25565}" python3 "${SCRIPTS_DIR}/player-count.py"
}
