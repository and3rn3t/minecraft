#!/bin/bash
# Bring the running server onto the newest image, restarting only when the
# image actually changed and nobody is playing.
#
# Run hourly by systemd/minecraft-update.timer, and by scripts/deploy-agent.sh
# after it rebuilds the image. The unit used to run
# `docker compose up -d --force-recreate` unconditionally every hour, which
# restarted the server whether or not a new image existed, kicking everyone off
# on the hour, and restarted servers that had been stopped on purpose.
#
# "Changed" means the image the container is running differs from the image
# its tag now points at. Comparing the two, rather than the tag before and
# after a pull, is what lets a restart deferred because someone was playing
# happen on a later run without anything new being pulled.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source-path=SCRIPTDIR
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

# The compose service and the container it creates are named differently;
# compose subcommands take the first, docker inspect takes the second.
SERVICE_NAME="minecraft"
CONTAINER_NAME="minecraft-server"

# Function to print usage
usage() {
    echo "Usage: $0 {run|check}"
    echo ""
    echo "Commands:"
    echo "  run    - Pull, and restart only if the image changed and nobody is online"
    echo "  check  - Report whether an update is available, change nothing"
    exit 1
}

# Function to get the image id the running container was started from
running_image_id() {
    docker inspect --format '{{.Image}}' "$CONTAINER_NAME" 2>/dev/null
}

# Function to get the image id the service's tag points at now
target_image_id() {
    local image
    # One service in the project, so the project's image list is its image
    image="$(compose config --images 2>/dev/null | head -1)"
    [ -n "$image" ] || return 1
    docker image inspect --format '{{.Id}}' "$image" 2>/dev/null
}

# Function to check whether the container is running right now
server_is_running() {
    [ -n "$(compose ps --status running --quiet "$SERVICE_NAME" 2>/dev/null)" ]
}

# Function to check whether the image is built here rather than pulled
builds_locally() {
    compose config 2>/dev/null | grep -qE '^[[:space:]]+build:'
}

# Function to fetch the newest image when it comes from a registry
fetch_image() {
    if builds_locally; then
        # Nothing to pull: deploy-agent.sh rebuilds when the Dockerfile changes
        return 0
    fi
    log_info "Pulling the latest image..."
    compose pull "$SERVICE_NAME"
}

# Function to pull and conditionally restart
run_update() {
    cd "$PROJECT_DIR" || return 1

    if ! take_update_lock; then
        log_info "A deploy is changing the server right now; checking again next run"
        return 0
    fi

    if ! server_is_running; then
        # A stopped server was stopped for a reason: bedtime, maintenance, or a
        # deliberate shutdown. Starting it again behind the owner's back is
        # worse than being a version behind.
        log_info "Server is not running; leaving it stopped"
        return 0
    fi

    if ! fetch_image; then
        log_warn "Pull failed; keeping the current image"
        return 0
    fi

    local running target
    running="$(running_image_id)"
    target="$(target_image_id)" || target=""

    if [ -z "$target" ] || [ "$running" = "$target" ]; then
        log_info "Already up to date; not restarting"
        return 0
    fi

    local online
    online="$(players_online 2>/dev/null)" || online=""
    case "$online" in
        '' | *[!0-9]*)
            log_warn "New image found, but the server did not say who is online; trying again next run"
            return 0
            ;;
    esac
    if [ "$online" -gt 0 ]; then
        log_warn "New image found, but ${online} player(s) online; restarting once the server is empty"
        return 0
    fi

    log_info "New image found; restarting the server"
    compose up -d "$SERVICE_NAME"
    log_success "Server updated"
}

# Function to report without changing anything
check_update() {
    cd "$PROJECT_DIR" || return 1

    if ! fetch_image; then
        log_error "Could not reach the registry"
        return 1
    fi

    local running target
    running="$(running_image_id)"
    target="$(target_image_id)" || target=""

    if [ -z "$target" ] || [ "$running" = "$target" ]; then
        log_info "Up to date"
    else
        log_warn "An update is available; run '$0 run' to apply it"
    fi
}

main() {
    case "${1:-}" in
        run)
            run_update
            ;;
        check)
            check_update
            ;;
        *)
            usage
            ;;
    esac
}

main "$@"
