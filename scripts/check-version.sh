#!/bin/bash
# Minecraft Version Checker
# Checks for available Minecraft server versions and compares with current version

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
CONFIG_FILE="${PROJECT_DIR}/config/update-check.conf"

# Default configuration
CHECK_ENABLED=true
CHECK_FREQUENCY="daily"
NOTIFY_ON_UPDATE=true

# Load configuration if it exists
if [ -f "$CONFIG_FILE" ]; then
    source "$CONFIG_FILE"
fi

# Function to get current version from docker-compose.yml
get_current_version() {
    local version=$(grep -E "MINECRAFT_VERSION=" "${PROJECT_DIR}/docker-compose.yml" | head -1 | sed 's/.*MINECRAFT_VERSION:-\([^}]*\).*/\1/' | sed 's/.*MINECRAFT_VERSION=\([^}]*\).*/\1/' | tr -d '"' | tr -d "'")
    if [ -z "$version" ]; then
        # Try environment variable
        version=${MINECRAFT_VERSION:-1.20.4}
    fi
    echo "$version"
}

# Function to get latest release version from Mojang API
get_latest_release() {
    local api_url="https://launchermeta.mojang.com/mc/game/version_manifest.json"
    local manifest=$(curl -s "$api_url" 2>/dev/null)

    if [ -z "$manifest" ]; then
        echo "ERROR: Failed to fetch version manifest" >&2
        return 1
    fi

    # Extract latest release version
    local latest=$(echo "$manifest" | grep -oP '"latest"\s*:\s*\{[^}]*"release"\s*:\s*"\K[^"]+' | head -1)
    echo "$latest"
}

# Function to get latest snapshot version
get_latest_snapshot() {
    local api_url="https://launchermeta.mojang.com/mc/game/version_manifest.json"
    local manifest=$(curl -s "$api_url" 2>/dev/null)

    if [ -z "$manifest" ]; then
        echo "ERROR: Failed to fetch version manifest" >&2
        return 1
    fi

    # Extract latest snapshot version
    local latest=$(echo "$manifest" | grep -oP '"latest"\s*:\s*\{[^}]*"snapshot"\s*:\s*"\K[^"]+' | head -1)
    echo "$latest"
}

# Function to get download URL for a version
get_version_download_url() {
    local version="$1"
    local api_url="https://launchermeta.mojang.com/mc/game/version_manifest.json"
    local manifest=$(curl -s "$api_url" 2>/dev/null)

    if [ -z "$manifest" ]; then
        echo "ERROR: Failed to fetch version manifest" >&2
        return 1
    fi

    # Find version entry
    local version_url=$(echo "$manifest" | grep -oP "\"id\"\s*:\s*\"$version\"[^}]*\"url\"\s*:\s*\"\K[^\"]+" | head -1)

    if [ -z "$version_url" ]; then
        echo "ERROR: Version $version not found" >&2
        return 1
    fi

    # Get version details
    local version_details=$(curl -s "$version_url" 2>/dev/null)

    if [ -z "$version_details" ]; then
        echo "ERROR: Failed to fetch version details" >&2
        return 1
    fi

    # Extract server jar URL
    local server_url=$(echo "$version_details" | grep -oP '"server"\s*:\s*\{[^}]*"url"\s*:\s*"\K[^"]+' | head -1)
    echo "$server_url"
}

# Function to compare versions
compare_versions() {
    local current="$1"
    local latest="$2"

    # Simple version comparison (assumes semantic versioning)
    # Convert to comparable format: 1.20.4 -> 1002004
    local current_num=$(echo "$current" | sed 's/\./0/g' | sed 's/[^0-9]//g')
    local latest_num=$(echo "$latest" | sed 's/\./0/g' | sed 's/[^0-9]//g')

    # Pad to same length
    local max_len=${#current_num}
    if [ ${#latest_num} -gt $max_len ]; then
        max_len=${#latest_num}
    fi

    current_num=$(printf "%0${max_len}d" "$current_num")
    latest_num=$(printf "%0${max_len}d" "$latest_num")

    if [ "$current_num" -lt "$latest_num" ]; then
        return 1  # Current is older
    elif [ "$current_num" -gt "$latest_num" ]; then
        return 2  # Current is newer
    else
        return 0  # Same version
    fi
}

# Main function
main() {
    if [ "$CHECK_ENABLED" != "true" ]; then
        echo "Version checking is disabled"
        exit 0
    fi

    echo -e "${BLUE}Checking Minecraft server versions...${NC}"

    local current=$(get_current_version)
    echo -e "Current version: ${GREEN}$current${NC}"

    local latest_release=$(get_latest_release)
    if [ $? -ne 0 ] || [ -z "$latest_release" ]; then
        echo -e "${RED}Failed to get latest release version${NC}"
        exit 1
    fi

    echo -e "Latest release: ${GREEN}$latest_release${NC}"

    compare_versions "$current" "$latest_release"
    local cmp_result=$?

    case $cmp_result in
        0)
            echo -e "${GREEN}You are running the latest release version!${NC}"
            exit 0
            ;;
        1)
            echo -e "${YELLOW}Update available: $current -> $latest_release${NC}"
            if [ "$NOTIFY_ON_UPDATE" = "true" ]; then
                echo -e "${YELLOW}Run './scripts/manage.sh update' to update${NC}"
            fi
            exit 0
            ;;
        2)
            echo -e "${BLUE}You are running a newer version than the latest release${NC}"
            echo -e "${BLUE}(You might be on a snapshot or custom build)${NC}"
            exit 0
            ;;
    esac
}

# If script is run directly
if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
    main "$@"
fi

