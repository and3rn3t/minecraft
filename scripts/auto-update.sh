#!/bin/bash
# Pull the latest server image and restart only if something actually changed.
#
# Run by systemd/minecraft-update.timer. The unit used to run
# `docker compose up -d --force-recreate` unconditionally every hour, which
# restarted the server whether or not a new image existed, kicking everyone off
# on the hour, and restarted servers that had been stopped on purpose.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source-path=SCRIPTDIR
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

SERVICE_NAME="minecraft-server"

# Function to print usage
usage() {
    echo "Usage: $0 {run|check}"
    echo ""
    echo "Commands:"
    echo "  run    - Pull, and restart only if the image changed"
    echo "  check  - Report whether an update is available, change nothing"
    exit 1
}

# Function to get the image id the service is currently using
current_image_id() {
    compose images -q "$SERVICE_NAME" 2>/dev/null | head -1
}

# Function to check whether the container is running right now
server_is_running() {
    [ -n "$(compose ps --status running --quiet "$SERVICE_NAME" 2>/dev/null)" ]
}

# Function to pull and conditionally restart
run_update() {
    if ! server_is_running; then
        # A stopped server was stopped for a reason: bedtime, maintenance, or a
        # deliberate shutdown. Starting it again behind the owner's back is
        # worse than being a version behind.
        log_info "Server is not running; leaving it stopped"
        return 0
    fi

    local before after
    before="$(current_image_id)"

    log_info "Pulling the latest image..."
    if ! compose pull "$SERVICE_NAME"; then
        log_warn "Pull failed; keeping the current image"
        return 0
    fi

    after="$(current_image_id)"

    if [ "$before" = "$after" ]; then
        log_info "Already up to date; not restarting"
        return 0
    fi

    log_info "New image found; restarting the server"
    compose up -d "$SERVICE_NAME"
    log_success "Server updated"
}

# Function to report without changing anything
check_update() {
    local before after
    before="$(current_image_id)"

    if ! compose pull "$SERVICE_NAME"; then
        log_error "Could not reach the registry"
        return 1
    fi

    after="$(current_image_id)"

    if [ "$before" = "$after" ]; then
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
