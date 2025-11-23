#!/bin/bash
# Mod Pack Installer Script
# Installs mod packs and resolves dependencies

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
SERVER_DIR="${SERVER_DIR:-${PROJECT_DIR}/data}"
MODS_DIR="${SERVER_DIR}/mods"
MODS_CACHE="${PROJECT_DIR}/.mods-cache"

# Create mods directory if it doesn't exist
mkdir -p "$MODS_DIR"
mkdir -p "$MODS_CACHE"

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to download file
download_file() {
    local url="$1"
    local output="$2"

    if command_exists curl; then
        curl -L -o "$output" "$url"
    elif command_exists wget; then
        wget -O "$output" "$url"
    else
        echo -e "${RED}Error: curl or wget required for downloads${NC}"
        return 1
    fi
}

# Function to resolve mod dependencies
resolve_dependencies() {
    local mod_file="$1"
    local loader_type="$2"

    echo -e "${BLUE}Resolving dependencies for: $(basename "$mod_file")${NC}"

    # Extract mod metadata (simplified - would need actual mod metadata parsing)
    # For now, return empty dependencies
    echo ""
}

# Function to install mod from URL
install_mod_from_url() {
    local mod_url="$1"
    local mod_name=$(basename "$mod_url")
    local mod_file="${MODS_DIR}/${mod_name}"

    echo -e "${BLUE}Downloading mod: $mod_name${NC}"

    if download_file "$mod_url" "$mod_file"; then
        echo -e "${GREEN}✓ Mod installed: $mod_name${NC}"
        return 0
    else
        echo -e "${RED}✗ Failed to download mod${NC}"
        return 1
    fi
}

# Function to install mod from file
install_mod_from_file() {
    local mod_file="$1"

    if [ ! -f "$mod_file" ]; then
        echo -e "${RED}Error: Mod file not found: $mod_file${NC}"
        return 1
    fi

    local mod_name=$(basename "$mod_file")
    local dest_file="${MODS_DIR}/${mod_name}"

    echo -e "${BLUE}Installing mod: $mod_name${NC}"

    if cp "$mod_file" "$dest_file"; then
        echo -e "${GREEN}✓ Mod installed: $mod_name${NC}"
        return 0
    else
        echo -e "${RED}✗ Failed to install mod${NC}"
        return 1
    fi
}

# Function to install mod pack from manifest
install_mod_pack() {
    local manifest_file="$1"

    if [ ! -f "$manifest_file" ]; then
        echo -e "${RED}Error: Manifest file not found: $manifest_file${NC}"
        return 1
    fi

    echo -e "${BLUE}Installing mod pack from manifest...${NC}"
    echo ""

    # Parse manifest (simplified JSON parsing)
    # Expected format: {"mods": [{"name": "...", "url": "..."}, ...]}

    local count=0
    local failed=0

    # Extract mod URLs from manifest (simplified)
    while IFS= read -r line; do
        if echo "$line" | grep -q '"url"'; then
            local url=$(echo "$line" | grep -oE 'https?://[^"]+' | head -1)
            if [ -n "$url" ]; then
                if install_mod_from_url "$url"; then
                    count=$((count + 1))
                else
                    failed=$((failed + 1))
                fi
            fi
        fi
    done < "$manifest_file"

    echo ""
    if [ $failed -eq 0 ]; then
        echo -e "${GREEN}✓ Mod pack installed: $count mod(s)${NC}"
        return 0
    else
        echo -e "${YELLOW}⚠ Mod pack partially installed: $count succeeded, $failed failed${NC}"
        return 1
    fi
}

# Function to remove mod
remove_mod() {
    local mod_name="$1"
    local mod_file="${MODS_DIR}/${mod_name}"

    if [ ! -f "$mod_file" ]; then
        echo -e "${YELLOW}Mod not found: $mod_name${NC}"
        return 1
    fi

    echo -e "${BLUE}Removing mod: $mod_name${NC}"

    if rm "$mod_file"; then
        echo -e "${GREEN}✓ Mod removed: $mod_name${NC}"
        return 0
    else
        echo -e "${RED}✗ Failed to remove mod${NC}"
        return 1
    fi
}

# Function to list installed mods
list_installed_mods() {
    echo -e "${BLUE}Installed Mods:${NC}"
    echo ""

    local count=0
    for mod_file in "$MODS_DIR"/*.jar; do
        if [ -f "$mod_file" ]; then
            echo "  - $(basename "$mod_file")"
            count=$((count + 1))
        fi
    done

    if [ $count -eq 0 ]; then
        echo -e "${YELLOW}No mods installed${NC}"
    else
        echo ""
        echo -e "${GREEN}Total: $count mod(s)${NC}"
    fi
}

# Function to update mod
update_mod() {
    local mod_name="$1"
    local mod_url="$2"

    if [ -z "$mod_url" ]; then
        echo -e "${RED}Error: Mod URL required for update${NC}"
        return 1
    fi

    # Remove old mod
    remove_mod "$mod_name" || true

    # Install new version
    install_mod_from_url "$mod_url"
}

# Function to verify mod compatibility
verify_compatibility() {
    local mod_file="$1"
    local loader_type="$2"
    local mc_version="$3"

    echo -e "${BLUE}Verifying compatibility...${NC}"
    echo "  Mod: $(basename "$mod_file")"
    echo "  Loader: $loader_type"
    echo "  Minecraft: $mc_version"

    # Simplified compatibility check
    # In reality, would parse mod metadata (fabric.mod.json, mods.toml, etc.)

    if [ ! -f "$mod_file" ]; then
        echo -e "${RED}✗ Mod file not found${NC}"
        return 1
    fi

    echo -e "${GREEN}✓ Mod file exists${NC}"
    return 0
}

# Main function
main() {
    local command="${1:-help}"

    case "$command" in
        install-url)
            if [ -z "$2" ]; then
                echo -e "${RED}Error: Mod URL required${NC}"
                exit 1
            fi
            install_mod_from_url "$2"
            ;;
        install-file)
            if [ -z "$2" ]; then
                echo -e "${RED}Error: Mod file path required${NC}"
                exit 1
            fi
            install_mod_from_file "$2"
            ;;
        install-pack)
            if [ -z "$2" ]; then
                echo -e "${RED}Error: Manifest file required${NC}"
                exit 1
            fi
            install_mod_pack "$2"
            ;;
        remove)
            if [ -z "$2" ]; then
                echo -e "${RED}Error: Mod name required${NC}"
                exit 1
            fi
            remove_mod "$2"
            ;;
        list)
            list_installed_mods
            ;;
        update)
            if [ -z "$2" ] || [ -z "$3" ]; then
                echo -e "${RED}Error: Mod name and URL required${NC}"
                exit 1
            fi
            update_mod "$2" "$3"
            ;;
        verify)
            if [ -z "$2" ]; then
                echo -e "${RED}Error: Mod file required${NC}"
                exit 1
            fi
            verify_compatibility "$2" "${3:-unknown}" "${4:-unknown}"
            ;;
        help|*)
            echo -e "${BLUE}Mod Pack Installer${NC}"
            echo ""
            echo "Usage: $0 {command} [options]"
            echo ""
            echo "Commands:"
            echo "  install-url <url>        - Install mod from URL"
            echo "  install-file <path>      - Install mod from local file"
            echo "  install-pack <manifest>  - Install mod pack from manifest"
            echo "  remove <mod-name>       - Remove installed mod"
            echo "  list                    - List installed mods"
            echo "  update <name> <url>     - Update mod to new version"
            echo "  verify <file> [loader] [mc-version] - Verify mod compatibility"
            echo "  help                    - Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0 install-url https://example.com/mod.jar"
            echo "  $0 install-file /path/to/mod.jar"
            echo "  $0 install-pack modpack.json"
            echo "  $0 remove some-mod.jar"
            echo "  $0 list"
            echo ""
            exit 1
            ;;
    esac
}

# Run main function
main "$@"

