#!/bin/bash
# Minecraft Server Management Script

set -e

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors, PROJECT_DIR and the compose() wrapper that prefers Docker Compose v2
# shellcheck source-path=SCRIPTDIR
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

# Function to display usage
usage() {
    echo -e "${BLUE}Minecraft Server Management Script${NC}"
    echo -e ""
    echo -e "Usage: $0 {start|stop|restart|status|logs|backup|restore|console|update|check-version|check-compatibility}"
    echo -e ""
    echo -e "Commands:"
    echo -e "  start              - Start the Minecraft server"
    echo -e "  stop               - Stop the Minecraft server"
    echo -e "  restart            - Restart the Minecraft server"
    echo -e "  status             - Check server status"
    echo -e "  logs               - View server logs"
    echo -e "  backup             - Create a backup of the server"
    echo -e "  restore <file>     - Restore a backup (stops server, moves data/ aside, extracts, starts)"
    echo -e "  console            - Attach to server console"
    echo -e "  update [ver]       - Update server to latest or specified version"
    echo -e "  check-version      - Check for available server updates"
    echo -e "  check-compatibility - Check compatibility before updating"
    echo -e "  plugins            - Plugin management (list, install, etc.)"
    echo -e "  logs-manage        - Log management (index, rotate, errors, stats)"
    echo -e "  logs-search        - Search server logs"
    echo -e "  worlds             - World management (list, create, switch, etc.)"
    echo -e "  rcon               - RCON client (send commands via RCON)"
    echo -e "  api                - API server management (start, stop, status)"
    exit 1
}

# Function to start server
start_server() {
    echo -e "${GREEN}Starting Minecraft server...${NC}"
    compose up -d
    echo -e "${GREEN}Server started! Use '$0 logs' to view logs${NC}"
}

# Function to stop server
stop_server() {
    echo -e "${YELLOW}Stopping Minecraft server...${NC}"
    compose down
    echo -e "${GREEN}Server stopped${NC}"
}

# Function to restart server
restart_server() {
    echo -e "${YELLOW}Restarting Minecraft server...${NC}"
    compose restart
    echo -e "${GREEN}Server restarted${NC}"
}

# Function to check status
check_status() {
    echo -e "${BLUE}Checking server status...${NC}"
    compose ps
}

# Function to view logs
view_logs() {
    echo -e "${BLUE}Viewing server logs (Press Ctrl+C to exit)...${NC}"
    compose logs -f
}

# Function to send command to server
send_server_command() {
    local command="$1"
    if ! docker ps | grep -q minecraft-server; then
        return 1
    fi

    # Try RCON first (if RCON is enabled and rcon-cli is available)
    if docker exec minecraft-server command -v rcon-cli >/dev/null 2>&1; then
        docker exec minecraft-server rcon-cli "$command" >/dev/null 2>&1 && return 0
    fi

    # Fallback: send command directly to Java process stdin
    # This works for vanilla servers without RCON
    local java_pid
    java_pid=$(docker exec minecraft-server pgrep -f java 2>/dev/null | head -1)
    if [ -n "$java_pid" ]; then
        echo "$command" | docker exec -i minecraft-server tee "/proc/$java_pid/fd/0" >/dev/null 2>&1 && return 0
    fi

    # Last resort: try docker attach method (non-blocking)
    echo "$command" | timeout 1 docker attach minecraft-server >/dev/null 2>&1 || true
    return 0
}

# Function to create backup
create_backup() {
    echo -e "${YELLOW}Creating backup...${NC}"
    BACKUP_DIR="./backups"
    mkdir -p "$BACKUP_DIR"

    # Check if server is running
    if docker ps | grep -q minecraft-server; then
        echo -e "${BLUE}Saving world before backup...${NC}"
        # Try multiple methods to send save-all command
        send_server_command "save-all"
        # Wait for save to complete (Minecraft needs a moment)
        sleep 3
        echo -e "${GREEN}World saved${NC}"
    fi

    TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
    BACKUP_FILE="$BACKUP_DIR/minecraft_backup_$TIMESTAMP.tar.gz"

    if [ ! -d "./data" ]; then
        echo -e "${RED}No data directory found${NC}"
        exit 1
    fi

    # Archive from inside a throwaway container of the server image rather
    # than on the host. It runs as the server's own user (uid 999), which owns
    # files the host's pi user can't read: Minecraft writes player data (every
    # inventory) mode 600, so a host-side tar failed on exactly the files that
    # matter most. `compose run` works whether or not the server is up. The
    # image has no gzip, so the host compresses.
    echo -e "${BLUE}Compressing backup...${NC}"
    local tar_log="${BACKUP_FILE}.log" tar_status gzip_status
    set +e
    compose run --rm --no-deps -T --entrypoint tar minecraft \
        -cf - -C /minecraft/server . 2>"$tar_log" | gzip > "$BACKUP_FILE"
    tar_status=${PIPESTATUS[0]} gzip_status=${PIPESTATUS[1]}
    set -e
    # tar exits 1 when a file changed while it was read (the live server
    # writing a region); the archive is still complete, so warn and go on.
    if [ "$tar_status" -eq 1 ] && [ "$gzip_status" -eq 0 ]; then
        echo -e "${YELLOW}Some files changed while being archived:${NC}"
        grep -i "changed" "$tar_log" || true
        tar_status=0
    fi
    if [ "$tar_status" -eq 0 ] && [ "$gzip_status" -eq 0 ]; then
        rm -f "$tar_log"
        BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
        echo -e "${GREEN}Backup created: $BACKUP_FILE (Size: $BACKUP_SIZE)${NC}"

        # Verify backup integrity
        echo -e "${BLUE}Verifying backup integrity...${NC}"
        if tar -tzf "$BACKUP_FILE" > /dev/null 2>&1; then
            FILE_COUNT=$(tar -tzf "$BACKUP_FILE" | wc -l)
            echo -e "${GREEN}Backup verified: $FILE_COUNT files archived${NC}"
        else
            echo -e "${RED}Warning: Backup verification failed${NC}"
            exit 1
        fi
    else
        echo -e "${RED}Backup creation failed (tar exit ${tar_status}, gzip exit ${gzip_status})${NC}"
        grep -v -i "memory.*limit" "$tar_log" | tail -20 || true
        rm -f "$BACKUP_FILE" "$tar_log"
        exit 1
    fi
}

# Function to restore a backup. Never deletes the current ./data: it is moved
# aside so a bad restore can be undone, and so this can never make a bad
# situation worse. "A backup that has never been restored is a hope, not a
# backup" -- this is also what makes that real, not just a script that exists.
restore_backup() {
    local backup_file="$1"
    if [ -z "$backup_file" ]; then
        echo -e "${RED}Usage: $0 restore <backup-file>${NC}"
        exit 1
    fi
    if [ ! -f "$backup_file" ]; then
        # Accept a bare filename too, resolved against ./backups
        backup_file="./backups/$(basename "$backup_file")"
        if [ ! -f "$backup_file" ]; then
            echo -e "${RED}Backup not found: $1${NC}"
            exit 1
        fi
    fi

    echo -e "${YELLOW}This stops the server and replaces ./data with $backup_file. Continue? (y/N)${NC}"
    read -p "" -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Cancelled"
        exit 0
    fi

    # Same lock deploy-agent.sh and auto-update.sh hold while they change the
    # running container, so a deploy landing mid-restore can't recreate it out
    # from under a data/ swap that is already in progress.
    if ! take_update_lock; then
        echo -e "${RED}A deploy or update is running; try the restore again once it finishes.${NC}"
        exit 1
    fi

    if docker ps | grep -q minecraft-server; then
        stop_server
    fi

    local aside=""
    if [ -d ./data ]; then
        aside="./data.pre-restore.$(date +%Y%m%d_%H%M%S)"
        echo -e "${BLUE}Moving current data aside: $aside${NC}"
        mv ./data "$aside"
    fi
    mkdir -p ./data

    echo -e "${BLUE}Extracting $backup_file...${NC}"
    if ! tar -xzf "$backup_file" -C ./data; then
        echo -e "${RED}Extraction failed; restoring previous ./data${NC}"
        rm -rf ./data
        [ -n "$aside" ] && mv "$aside" ./data
        exit 1
    fi

    echo -e "${GREEN}Starting server...${NC}"
    start_server

    echo -e "${BLUE}Watching logs for a clean world load (up to 60s)...${NC}"
    # compose() is a shell function, not visible to the `bash -c` below; resolve
    # the real command first. Wrapped in `timeout ... bash -c` (rather than
    # piping into `timeout grep`) so a `logs -f` that never produces a match
    # is killed too, instead of leaving grep's read end of the pipe orphaned.
    local compose_bin match
    compose_bin="$(compose_cmd)"
    # grep exits non-zero when nothing matches (including on a plain timeout);
    # that is an expected outcome here, inspected via $match below, not a
    # script-ending error -- `|| true` keeps `set -e` from exiting first.
    match="$(timeout 60 bash -c "$compose_bin logs -f minecraft 2>/dev/null | grep -m1 -E 'Done \\(|FAILED TO LOAD WORLD|Exception'")" || true

    case "$match" in
        *'Done ('*)
            echo -e "${GREEN}World loaded cleanly: ${match}${NC}"
            ;;
        '')
            echo -e "${RED}No clean-load confirmation seen within 60s; check '$0 logs' by hand.${NC}"
            exit 1
            ;;
        *)
            echo -e "${RED}World failed to load: ${match}${NC}"
            exit 1
            ;;
    esac

    if [ -n "$aside" ]; then
        echo -e "${YELLOW}Previous data kept at: $aside (remove it by hand once you've confirmed the restore)${NC}"
    fi
}

# Function to attach to console
attach_console() {
    echo -e "${BLUE}Attaching to server console (Press Ctrl+P then Ctrl+Q to detach)...${NC}"
    docker attach minecraft-server
}

# Function to update configuration
update_config() {
    echo -e "${YELLOW}Pulling latest configuration...${NC}"
    git pull
    echo -e "${GREEN}Configuration updated. Run '$0 restart' to apply changes${NC}"
}

# Function to update server version
update_server() {
    echo -e "${BLUE}Checking for server updates...${NC}"

    # Check current version
    local current_version
    current_version=$(grep -E "MINECRAFT_VERSION=" docker-compose.yml | head -1 | sed 's/.*MINECRAFT_VERSION:-\([^}]*\).*/\1/' | sed 's/.*MINECRAFT_VERSION=\([^}]*\).*/\1/' | tr -d '"' | tr -d "'" || echo "1.20.4")
    current_version=${current_version:-${MINECRAFT_VERSION:-1.20.4}}

    echo -e "Current version: ${GREEN}$current_version${NC}"

    # Check for updates
    local latest_version
    latest_version=$("${SCRIPT_DIR}/check-version.sh" 2>/dev/null | grep "Latest release:" | awk '{print $3}' || echo "")

    if [ -z "$latest_version" ]; then
        # Try to get latest version directly
        local api_url="https://launchermeta.mojang.com/mc/game/version_manifest.json"
        latest_version=$(curl -s "$api_url" 2>/dev/null | grep -oP '"latest"\s*:\s*\{[^}]*"release"\s*:\s*"\K[^"]+' | head -1)
    fi

    if [ -z "$latest_version" ]; then
        echo -e "${RED}Failed to get latest version. Please specify version manually.${NC}"
        echo -e "${YELLOW}Usage: $0 update <version>${NC}"
        exit 1
    fi

    echo -e "Latest version: ${GREEN}$latest_version${NC}"

    # Ask for confirmation if versions differ
    if [ "$current_version" != "$latest_version" ]; then
        echo -e "${YELLOW}Update available: $current_version -> $latest_version${NC}"
        read -p "Do you want to update? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo -e "${YELLOW}Update cancelled${NC}"
            exit 0
        fi
    else
        echo -e "${GREEN}Already on latest version${NC}"
        exit 0
    fi

    local target_version="${1:-$latest_version}"
    local server_type=${SERVER_TYPE:-vanilla}

    echo -e "${YELLOW}Updating to version $target_version...${NC}"

    # Create backup before update
    echo -e "${BLUE}Creating backup before update...${NC}"
    create_backup

    # Stop server
    echo -e "${YELLOW}Stopping server...${NC}"
    stop_server

    # Download new server jar
    echo -e "${BLUE}Downloading server jar...${NC}"
    if [ -f "${SCRIPT_DIR}/download-server.sh" ]; then
        "${SCRIPT_DIR}/download-server.sh" --type "$server_type" --version "$target_version" --output "./data"
    else
        echo -e "${RED}download-server.sh not found${NC}"
        exit 1
    fi

    # Update docker-compose.yml
    echo -e "${BLUE}Updating docker-compose.yml...${NC}"
    if [ -f "docker-compose.yml" ]; then
        # Backup docker-compose.yml
        cp docker-compose.yml docker-compose.yml.bak

        # Update version in docker-compose.yml
        sed -i.bak "s/MINECRAFT_VERSION:-[^}]*/MINECRAFT_VERSION:-$target_version/g" docker-compose.yml
        sed -i.bak "s/MINECRAFT_VERSION=[^}]*/MINECRAFT_VERSION=$target_version/g" docker-compose.yml
        rm -f docker-compose.yml.bak
    fi

    # Update .env if it exists
    if [ -f ".env" ]; then
        if grep -q "MINECRAFT_VERSION" .env; then
            sed -i.bak "s/MINECRAFT_VERSION=.*/MINECRAFT_VERSION=$target_version/" .env
            rm -f .env.bak
        else
            echo "MINECRAFT_VERSION=$target_version" >> .env
        fi
    fi

    # Rebuild and start
    echo -e "${BLUE}Rebuilding container...${NC}"
    compose build --no-cache

    echo -e "${GREEN}Starting server with new version...${NC}"
    start_server

    echo -e "${GREEN}Update complete! Server is now running version $target_version${NC}"
    echo -e "${YELLOW}Note: If the server fails to start, you can restore from backup${NC}"
}

# Main script logic
case "${1}" in
    start)
        start_server
        ;;
    stop)
        stop_server
        ;;
    restart)
        restart_server
        ;;
    status)
        check_status
        ;;
    logs)
        view_logs
        ;;
    backup)
        create_backup
        ;;
    restore)
        restore_backup "$2"
        ;;
    console)
        attach_console
        ;;
    update)
        # Check compatibility before updating
        if [ -f "${SCRIPT_DIR}/check-compatibility.sh" ]; then
            current_version=$(grep -E "MINECRAFT_VERSION=" docker-compose.yml | head -1 | sed 's/.*MINECRAFT_VERSION:-\([^}]*\).*/\1/' | sed 's/.*MINECRAFT_VERSION=\([^}]*\).*/\1/' | tr -d '"' | tr -d "'" || echo "1.20.4")
            current_version=${current_version:-${MINECRAFT_VERSION:-1.20.4}}
            target_version="${2:-}"

            if [ -n "$target_version" ]; then
                echo -e "${BLUE}Running compatibility check...${NC}"
                if ! "${SCRIPT_DIR}/check-compatibility.sh" "$target_version" "$current_version"; then
                    read -p "Continue with update despite warnings? (y/N): " -n 1 -r
                    echo
                    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                        echo -e "${YELLOW}Update cancelled${NC}"
                        exit 0
                    fi
                fi
            fi
        fi
        update_server "$2"
        ;;
    check-version)
        if [ -f "${SCRIPT_DIR}/check-version.sh" ]; then
            "${SCRIPT_DIR}/check-version.sh"
        else
            echo -e "${RED}check-version.sh not found${NC}"
            exit 1
        fi
        ;;
    check-compatibility)
        if [ -f "${SCRIPT_DIR}/check-compatibility.sh" ]; then
            "${SCRIPT_DIR}/check-compatibility.sh" "$2" "$3"
        else
            echo -e "${RED}check-compatibility.sh not found${NC}"
            exit 1
        fi
        ;;
    plugins)
        if [ -f "${SCRIPT_DIR}/plugin-manager.sh" ]; then
            shift
            "${SCRIPT_DIR}/plugin-manager.sh" "$@"
        else
            echo -e "${RED}plugin-manager.sh not found${NC}"
            exit 1
        fi
        ;;
    logs-manage)
        if [ -f "${SCRIPT_DIR}/log-manager.sh" ]; then
            shift
            "${SCRIPT_DIR}/log-manager.sh" "$@"
        else
            echo -e "${RED}log-manager.sh not found${NC}"
            exit 1
        fi
        ;;
    logs-search)
        if [ -f "${SCRIPT_DIR}/log-search.sh" ]; then
            shift
            "${SCRIPT_DIR}/log-search.sh" "$@"
        else
            echo -e "${RED}log-search.sh not found${NC}"
            exit 1
        fi
        ;;
    worlds)
        if [ -f "${SCRIPT_DIR}/world-manager.sh" ]; then
            shift
            "${SCRIPT_DIR}/world-manager.sh" "$@"
        else
            echo -e "${RED}world-manager.sh not found${NC}"
            exit 1
        fi
        ;;
    rcon)
        if [ -f "${SCRIPT_DIR}/rcon-client.sh" ]; then
            shift
            "${SCRIPT_DIR}/rcon-client.sh" "$@"
        else
            echo -e "${RED}rcon-client.sh not found${NC}"
            exit 1
        fi
        ;;
    api)
        if [ -f "${SCRIPT_DIR}/api-server.sh" ]; then
            shift
            "${SCRIPT_DIR}/api-server.sh" "$@"
        else
            echo -e "${RED}api-server.sh not found${NC}"
            exit 1
        fi
        ;;
    *)
        usage
        ;;
esac
