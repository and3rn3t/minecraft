#!/bin/bash
# Version Compatibility Checker
# Checks world, plugin, and mod compatibility before updates

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
DATA_DIR="${PROJECT_DIR}/data"

# Function to get world version
get_world_version() {
    local world_dir="$1"
    if [ ! -d "$world_dir" ]; then
        return 1
    fi

    # Check level.dat for version
    if [ -f "$world_dir/level.dat" ]; then
        # Use nbtdump or similar tool if available, otherwise return unknown
        # For now, we'll check the world directory structure
        if [ -d "$world_dir/data" ] && [ -f "$world_dir/level.dat" ]; then
            # Modern world format (1.2+)
            echo "modern"
        else
            echo "legacy"
        fi
    else
        return 1
    fi
}

# Function to check version compatibility
check_version_compatibility() {
    local current_version="$1"
    local target_version="$2"

    # Extract major and minor version numbers
    local current_major=$(echo "$current_version" | cut -d'.' -f1)
    local current_minor=$(echo "$current_version" | cut -d'.' -f2)
    local target_major=$(echo "$target_version" | cut -d'.' -f1)
    local target_minor=$(echo "$target_version" | cut -d'.' -f2)

    # Major version changes usually require world conversion
    if [ "$current_major" -ne "$target_major" ]; then
        echo "MAJOR_VERSION_CHANGE"
        return 1
    fi

    # Minor version changes within same major are usually compatible
    if [ "$current_minor" -ne "$target_minor" ]; then
        local diff=$((target_minor - current_minor))
        if [ $diff -gt 2 ]; then
            echo "LARGE_MINOR_VERSION_CHANGE"
            return 1
        else
            echo "MINOR_VERSION_CHANGE"
            return 0
        fi
    fi

    echo "SAME_VERSION"
    return 0
}

# Function to check world compatibility
check_world_compatibility() {
    local target_version="$1"
    local issues=0

    echo -e "${BLUE}Checking world compatibility...${NC}"

    # Check main world
    if [ -d "${DATA_DIR}/world" ]; then
        local world_version=$(get_world_version "${DATA_DIR}/world")
        if [ -z "$world_version" ]; then
            echo -e "${YELLOW}Warning: Could not determine world version${NC}"
            issues=$((issues + 1))
        else
            echo -e "${GREEN}Main world format: $world_version${NC}"
        fi
    fi

    # Check nether world
    if [ -d "${DATA_DIR}/world_nether" ]; then
        echo -e "${GREEN}Nether world found${NC}"
    fi

    # Check end world
    if [ -d "${DATA_DIR}/world_the_end" ]; then
        echo -e "${GREEN}End world found${NC}"
    fi

    if [ $issues -eq 0 ]; then
        echo -e "${GREEN}World compatibility check passed${NC}"
        return 0
    else
        echo -e "${YELLOW}World compatibility check found $issues warning(s)${NC}"
        return 1
    fi
}

# Function to check plugin compatibility
check_plugin_compatibility() {
    local target_version="$1"
    local issues=0

    echo -e "${BLUE}Checking plugin compatibility...${NC}"

    if [ ! -d "${DATA_DIR}/plugins" ] && [ ! -d "${PROJECT_DIR}/plugins" ]; then
        echo -e "${GREEN}No plugins installed${NC}"
        return 0
    fi

    local plugin_dir="${DATA_DIR}/plugins"
    if [ ! -d "$plugin_dir" ]; then
        plugin_dir="${PROJECT_DIR}/plugins"
    fi

    if [ ! -d "$plugin_dir" ]; then
        return 0
    fi

    local plugin_count=0
    for plugin in "$plugin_dir"/*.jar; do
        if [ -f "$plugin" ]; then
            plugin_count=$((plugin_count + 1))
            local plugin_name=$(basename "$plugin")
            echo -e "${YELLOW}Plugin found: $plugin_name${NC}"
            echo -e "${YELLOW}  Note: Manual verification recommended for version $target_version${NC}"
            issues=$((issues + 1))
        fi
    done

    if [ $plugin_count -eq 0 ]; then
        echo -e "${GREEN}No plugins found${NC}"
        return 0
    fi

    echo -e "${YELLOW}Found $plugin_count plugin(s) - manual compatibility check recommended${NC}"
    return 1
}

# Function to check mod compatibility
check_mod_compatibility() {
    local target_version="$1"

    echo -e "${BLUE}Checking mod compatibility...${NC}"

    # Check for mods directory (Fabric/Forge)
    if [ -d "${DATA_DIR}/mods" ]; then
        local mod_count=$(find "${DATA_DIR}/mods" -name "*.jar" | wc -l)
        if [ $mod_count -gt 0 ]; then
            echo -e "${YELLOW}Found $mod_count mod(s) - manual compatibility check required${NC}"
            echo -e "${YELLOW}  Mods are version-specific and may not work with $target_version${NC}"
            return 1
        fi
    fi

    echo -e "${GREEN}No mods found${NC}"
    return 0
}

# Function to validate configuration files
validate_configuration() {
    echo -e "${BLUE}Validating configuration files...${NC}"

    local issues=0

    # Check server.properties
    if [ -f "${DATA_DIR}/server.properties" ]; then
        if ! grep -q "^server-port=" "${DATA_DIR}/server.properties" 2>/dev/null; then
            echo -e "${YELLOW}Warning: server.properties may be missing required settings${NC}"
            issues=$((issues + 1))
        else
            echo -e "${GREEN}server.properties looks valid${NC}"
        fi
    fi

    # Check eula.txt
    if [ -f "${DATA_DIR}/eula.txt" ]; then
        if ! grep -q "eula=true" "${DATA_DIR}/eula.txt" 2>/dev/null; then
            echo -e "${YELLOW}Warning: EULA not accepted${NC}"
            issues=$((issues + 1))
        else
            echo -e "${GREEN}EULA accepted${NC}"
        fi
    fi

    if [ $issues -eq 0 ]; then
        echo -e "${GREEN}Configuration validation passed${NC}"
        return 0
    else
        echo -e "${YELLOW}Configuration validation found $issues issue(s)${NC}"
        return 1
    fi
}

# Main function
main() {
    local target_version="${1:-}"
    local current_version="${2:-}"

    if [ -z "$target_version" ]; then
        echo -e "${RED}Error: Target version not specified${NC}"
        echo -e "${YELLOW}Usage: $0 <target_version> [current_version]${NC}"
        exit 1
    fi

    if [ -z "$current_version" ]; then
        # Try to get current version from docker-compose.yml
        current_version=$(grep -E "MINECRAFT_VERSION=" "${PROJECT_DIR}/docker-compose.yml" | head -1 | sed 's/.*MINECRAFT_VERSION:-\([^}]*\).*/\1/' | sed 's/.*MINECRAFT_VERSION=\([^}]*\).*/\1/' | tr -d '"' | tr -d "'" || echo "1.20.4")
        current_version=${current_version:-${MINECRAFT_VERSION:-1.20.4}}
    fi

    echo -e "${BLUE}Compatibility Check${NC}"
    echo -e "${BLUE}===================${NC}"
    echo -e "Current version: ${GREEN}$current_version${NC}"
    echo -e "Target version: ${GREEN}$target_version${NC}"
    echo ""

    local overall_issues=0

    # Check version compatibility
    local version_check=$(check_version_compatibility "$current_version" "$target_version")
    case "$version_check" in
        MAJOR_VERSION_CHANGE)
            echo -e "${RED}WARNING: Major version change detected${NC}"
            echo -e "${YELLOW}  World conversion may be required${NC}"
            overall_issues=$((overall_issues + 1))
            ;;
        LARGE_MINOR_VERSION_CHANGE)
            echo -e "${YELLOW}WARNING: Large minor version change${NC}"
            echo -e "${YELLOW}  Compatibility issues may occur${NC}"
            overall_issues=$((overall_issues + 1))
            ;;
        MINOR_VERSION_CHANGE)
            echo -e "${GREEN}Minor version change - should be compatible${NC}"
            ;;
        SAME_VERSION)
            echo -e "${GREEN}Same version - no compatibility issues expected${NC}"
            ;;
    esac
    echo ""

    # Check world compatibility
    if ! check_world_compatibility "$target_version"; then
        overall_issues=$((overall_issues + 1))
    fi
    echo ""

    # Check plugin compatibility
    if ! check_plugin_compatibility "$target_version"; then
        overall_issues=$((overall_issues + 1))
    fi
    echo ""

    # Check mod compatibility
    if ! check_mod_compatibility "$target_version"; then
        overall_issues=$((overall_issues + 1))
    fi
    echo ""

    # Validate configuration
    if ! validate_configuration; then
        overall_issues=$((overall_issues + 1))
    fi
    echo ""

    # Summary
    echo -e "${BLUE}===================${NC}"
    if [ $overall_issues -eq 0 ]; then
        echo -e "${GREEN}Compatibility check passed!${NC}"
        echo -e "${GREEN}Safe to update to $target_version${NC}"
        exit 0
    else
        echo -e "${YELLOW}Compatibility check found $overall_issues issue(s)${NC}"
        echo -e "${YELLOW}Review warnings above before updating${NC}"
        exit 1
    fi
}

# Run main function
main "$@"

