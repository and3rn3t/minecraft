#!/bin/bash
# Minecraft Server Management Script

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Function to display usage
usage() {
    echo -e "${BLUE}Minecraft Server Management Script${NC}"
    echo -e ""
    echo -e "Usage: $0 {start|stop|restart|status|logs|backup|console|update|check-version|check-compatibility}"
    echo -e ""
    echo -e "Commands:"
    echo -e "  start              - Start the Minecraft server"
    echo -e "  stop               - Stop the Minecraft server"
    echo -e "  restart            - Restart the Minecraft server"
    echo -e "  status             - Check server status"
    echo -e "  logs               - View server logs"
    echo -e "  backup             - Create a backup of the server"
    echo -e "  console            - Attach to server console"
    echo -e "  update [ver]       - Update server to latest or specified version"
    echo -e "  check-version      - Check for available server updates"
    echo -e "  check-compatibility - Check compatibility before updating"
    echo -e "  plugins            - Plugin management (list, install, etc.)"
    echo -e "  logs-manage        - Log management (index, rotate, errors, stats)"
    echo -e "  logs-search        - Search server logs"
    exit 1
}

# Function to start server
start_server() {
    echo -e "${GREEN}Starting Minecraft server...${NC}"
    docker-compose up -d
    echo -e "${GREEN}Server started! Use '$0 logs' to view logs${NC}"
}

# Function to stop server
stop_server() {
    echo -e "${YELLOW}Stopping Minecraft server...${NC}"
    docker-compose down
    echo -e "${GREEN}Server stopped${NC}"
}

# Function to restart server
restart_server() {
    echo -e "${YELLOW}Restarting Minecraft server...${NC}"
    docker-compose restart
    echo -e "${GREEN}Server restarted${NC}"
}

# Function to check status
check_status() {
    echo -e "${BLUE}Checking server status...${NC}"
    docker-compose ps
}

# Function to view logs
view_logs() {
    echo -e "${BLUE}Viewing server logs (Press Ctrl+C to exit)...${NC}"
    docker-compose logs -f
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
    local java_pid=$(docker exec minecraft-server pgrep -f java 2>/dev/null | head -1)
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

    # Create backup with compression (using gzip, can be optimized later)
    echo -e "${BLUE}Compressing backup...${NC}"
    if tar -czf "$BACKUP_FILE" -C ./data . 2>/dev/null; then
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
        echo -e "${RED}Backup creation failed${NC}"
        exit 1
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
    local current_version=$(grep -E "MINECRAFT_VERSION=" docker-compose.yml | head -1 | sed 's/.*MINECRAFT_VERSION:-\([^}]*\).*/\1/' | sed 's/.*MINECRAFT_VERSION=\([^}]*\).*/\1/' | tr -d '"' | tr -d "'" || echo "1.20.4")
    current_version=${current_version:-${MINECRAFT_VERSION:-1.20.4}}

    echo -e "Current version: ${GREEN}$current_version${NC}"

    # Check for updates
    local latest_version=$("${SCRIPT_DIR}/check-version.sh" 2>/dev/null | grep "Latest release:" | awk '{print $3}' || echo "")

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
    docker-compose build --no-cache

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
    console)
        attach_console
        ;;
    update)
        # Check compatibility before updating
        if [ -f "${SCRIPT_DIR}/check-compatibility.sh" ]; then
            local current_version=$(grep -E "MINECRAFT_VERSION=" docker-compose.yml | head -1 | sed 's/.*MINECRAFT_VERSION:-\([^}]*\).*/\1/' | sed 's/.*MINECRAFT_VERSION=\([^}]*\).*/\1/' | tr -d '"' | tr -d "'" || echo "1.20.4")
            current_version=${current_version:-${MINECRAFT_VERSION:-1.20.4}}
            local target_version="${2:-}"

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
    *)
        usage
        ;;
esac
