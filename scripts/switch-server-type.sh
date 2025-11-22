#!/bin/bash
# Server Type Switcher
# Switches between different server implementations (Vanilla, Paper, Spigot, Fabric)

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

# Supported server types
SUPPORTED_TYPES="vanilla paper spigot fabric"

# Function to get current server type
get_current_type() {
    local type=$(grep -E "SERVER_TYPE=" "${PROJECT_DIR}/docker-compose.yml" | head -1 | sed 's/.*SERVER_TYPE:-\([^}]*\).*/\1/' | sed 's/.*SERVER_TYPE=\([^}]*\).*/\1/' | tr -d '"' | tr -d "'" || echo "vanilla")
    type=${type:-${SERVER_TYPE:-vanilla}}
    echo "$type"
}

# Function to set server type
set_server_type() {
    local new_type="$1"

    # Validate server type
    if ! echo "$SUPPORTED_TYPES" | grep -q "$new_type"; then
        echo -e "${RED}Unsupported server type: $new_type${NC}"
        echo -e "${YELLOW}Supported types: $SUPPORTED_TYPES${NC}"
        exit 1
    fi

    local current_type=$(get_current_type)

    if [ "$current_type" = "$new_type" ]; then
        echo -e "${GREEN}Server is already set to $new_type${NC}"
        exit 0
    fi

    echo -e "${YELLOW}Switching from $current_type to $new_type...${NC}"

    # Check if server is running
    if docker ps | grep -q minecraft-server; then
        echo -e "${YELLOW}Server is running. Stopping first...${NC}"
        cd "$PROJECT_DIR"
        ./scripts/manage.sh stop
    fi

    # Update docker-compose.yml
    echo -e "${BLUE}Updating docker-compose.yml...${NC}"
    if [ -f "${PROJECT_DIR}/docker-compose.yml" ]; then
        # Backup docker-compose.yml
        cp "${PROJECT_DIR}/docker-compose.yml" "${PROJECT_DIR}/docker-compose.yml.bak"

        # Update SERVER_TYPE
        sed -i.bak "s/SERVER_TYPE:-[^}]*/SERVER_TYPE:-$new_type/g" "${PROJECT_DIR}/docker-compose.yml"
        sed -i.bak "s/SERVER_TYPE=[^}]*/SERVER_TYPE=$new_type/g" "${PROJECT_DIR}/docker-compose.yml"
        rm -f "${PROJECT_DIR}/docker-compose.yml.bak"
    fi

    # Update .env if it exists
    if [ -f "${PROJECT_DIR}/.env" ]; then
        if grep -q "SERVER_TYPE" "${PROJECT_DIR}/.env"; then
            sed -i.bak "s/SERVER_TYPE=.*/SERVER_TYPE=$new_type/" "${PROJECT_DIR}/.env"
            rm -f "${PROJECT_DIR}/.env.bak"
        else
            echo "SERVER_TYPE=$new_type" >> "${PROJECT_DIR}/.env"
        fi
    fi

    # Determine jar filename based on type
    local jar_name="server.jar"
    case "$new_type" in
        paper)
            local version=${MINECRAFT_VERSION:-1.20.4}
            jar_name="paper-${version}.jar"
            ;;
        fabric)
            jar_name="fabric-server.jar"
            ;;
        spigot)
            jar_name="spigot.jar"
            ;;
        vanilla)
            jar_name="server.jar"
            ;;
    esac

    # Check if server jar exists for new type
    if [ ! -f "${PROJECT_DIR}/data/${jar_name}" ]; then
        echo -e "${YELLOW}Server jar for $new_type not found. Downloading...${NC}"
        cd "$PROJECT_DIR"
        if [ -f "${SCRIPT_DIR}/download-server.sh" ]; then
            local version=${MINECRAFT_VERSION:-1.20.4}
            "${SCRIPT_DIR}/download-server.sh" --type "$new_type" --version "$version" --output "./data"
        else
            echo -e "${RED}download-server.sh not found${NC}"
            exit 1
        fi
    fi

    echo -e "${GREEN}Server type switched to $new_type${NC}"
    echo -e "${YELLOW}Run './scripts/manage.sh start' to start the server${NC}"
}

# Function to list available types
list_types() {
    echo -e "${BLUE}Available server types:${NC}"
    for type in $SUPPORTED_TYPES; do
        local current=$(get_current_type)
        if [ "$type" = "$current" ]; then
            echo -e "  ${GREEN}* $type (current)${NC}"
        else
            echo -e "    $type"
        fi
    done
}

# Main function
main() {
    if [ $# -eq 0 ]; then
        list_types
        exit 0
    fi

    case "$1" in
        list)
            list_types
            ;;
        current)
            echo -e "Current server type: ${GREEN}$(get_current_type)${NC}"
            ;;
        *)
            set_server_type "$1"
            ;;
    esac
}

# Run main function
main "$@"

