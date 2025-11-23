#!/bin/bash
# Mod Loader Detection Script
# Detects installed mod loaders (Forge, Fabric, Quilt)

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

# Function to detect Forge
detect_forge() {
    local mods_dir="${SERVER_DIR}/mods"
    local server_jar="${SERVER_DIR}/server.jar"

    # Check for Forge mods directory
    if [ -d "$mods_dir" ]; then
        # Check for Forge-specific files
        if [ -f "${SERVER_DIR}/libraries/net/minecraftforge/forge" ] || \
           [ -f "${SERVER_DIR}/libraries/net/minecraftforge" ] || \
           grep -q "forge" "${server_jar}" 2>/dev/null; then
            return 0
        fi

        # Check for Forge mod files
        if find "$mods_dir" -name "*.jar" -type f | grep -q "forge" 2>/dev/null; then
            return 0
        fi
    fi

    # Check server jar name for Forge
    if echo "$server_jar" | grep -qi "forge"; then
        return 0
    fi

    return 1
}

# Function to detect Fabric
detect_fabric() {
    local mods_dir="${SERVER_DIR}/mods"
    local server_jar="${SERVER_DIR}/server.jar"

    # Check for Fabric API
    if [ -d "$mods_dir" ]; then
        if find "$mods_dir" -name "fabric-api*.jar" -o -name "fabric*.jar" | grep -q . 2>/dev/null; then
            return 0
        fi
    fi

    # Check for Fabric loader in libraries
    if [ -d "${SERVER_DIR}/libraries" ]; then
        if find "${SERVER_DIR}/libraries" -path "*/net/fabricmc/*" -type d | grep -q . 2>/dev/null; then
            return 0
        fi
    fi

    # Check server jar name for Fabric
    if echo "$server_jar" | grep -qi "fabric"; then
        return 0
    fi

    return 1
}

# Function to detect Quilt
detect_quilt() {
    local mods_dir="${SERVER_DIR}/mods"
    local server_jar="${SERVER_DIR}/server.jar"

    # Check for Quilt Loader
    if [ -d "$mods_dir" ]; then
        if find "$mods_dir" -name "quilt-loader*.jar" -o -name "quilt*.jar" | grep -q . 2>/dev/null; then
            return 0
        fi
    fi

    # Check for Quilt in libraries
    if [ -d "${SERVER_DIR}/libraries" ]; then
        if find "${SERVER_DIR}/libraries" -path "*/org/quiltmc/*" -type d | grep -q . 2>/dev/null; then
            return 0
        fi
    fi

    # Check server jar name for Quilt
    if echo "$server_jar" | grep -qi "quilt"; then
        return 0
    fi

    return 1
}

# Function to get mod loader version
get_forge_version() {
    local server_jar="${SERVER_DIR}/server.jar"
    local version_file="${SERVER_DIR}/version.json"

    # Try to extract from version.json
    if [ -f "$version_file" ]; then
        local version=$(grep -o '"forge"[^}]*' "$version_file" 2>/dev/null | grep -o '[0-9]\+\.[0-9]\+\.[0-9]\+' | head -1)
        if [ -n "$version" ]; then
            echo "$version"
            return 0
        fi
    fi

    # Try to extract from server jar name
    if echo "$server_jar" | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1; then
        return 0
    fi

    echo "unknown"
}

# Function to get Fabric version
get_fabric_version() {
    local mods_dir="${SERVER_DIR}/mods"
    local fabric_jar=$(find "$mods_dir" -name "fabric-loader*.jar" 2>/dev/null | head -1)

    if [ -n "$fabric_jar" ]; then
        # Extract version from filename
        basename "$fabric_jar" | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1 || echo "unknown"
    else
        echo "unknown"
    fi
}

# Function to get Quilt version
get_quilt_version() {
    local mods_dir="${SERVER_DIR}/mods"
    local quilt_jar=$(find "$mods_dir" -name "quilt-loader*.jar" 2>/dev/null | head -1)

    if [ -n "$quilt_jar" ]; then
        # Extract version from filename
        basename "$quilt_jar" | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1 || echo "unknown"
    else
        echo "unknown"
    fi
}

# Function to detect all mod loaders
detect_all() {
    local loaders=()

    if detect_forge; then
        local version=$(get_forge_version)
        loaders+=("Forge:${version}")
    fi

    if detect_fabric; then
        local version=$(get_fabric_version)
        loaders+=("Fabric:${version}")
    fi

    if detect_quilt; then
        local version=$(get_quilt_version)
        loaders+=("Quilt:${version}")
    fi

    if [ ${#loaders[@]} -eq 0 ]; then
        echo "none"
    else
        IFS=','; echo "${loaders[*]}"
    fi
}

# Function to list detected mods
list_mods() {
    local mods_dir="${SERVER_DIR}/mods"

    if [ ! -d "$mods_dir" ]; then
        echo -e "${YELLOW}No mods directory found${NC}"
        return 1
    fi

    echo -e "${BLUE}Installed Mods:${NC}"
    echo ""

    local count=0
    for mod_file in "$mods_dir"/*.jar; do
        if [ -f "$mod_file" ]; then
            local mod_name=$(basename "$mod_file")
            echo "  - $mod_name"
            count=$((count + 1))
        fi
    done

    if [ $count -eq 0 ]; then
        echo -e "${YELLOW}No mods found${NC}"
    else
        echo ""
        echo -e "${GREEN}Total: $count mod(s)${NC}"
    fi
}

# Main function
main() {
    local command="${1:-detect}"

    case "$command" in
        detect)
            local result=$(detect_all)
            if [ "$result" = "none" ]; then
                echo -e "${YELLOW}No mod loader detected${NC}"
                exit 1
            else
                echo -e "${GREEN}Detected mod loader(s): $result${NC}"
                exit 0
            fi
            ;;
        forge)
            if detect_forge; then
                local version=$(get_forge_version)
                echo -e "${GREEN}Forge detected (version: $version)${NC}"
                exit 0
            else
                echo -e "${YELLOW}Forge not detected${NC}"
                exit 1
            fi
            ;;
        fabric)
            if detect_fabric; then
                local version=$(get_fabric_version)
                echo -e "${GREEN}Fabric detected (version: $version)${NC}"
                exit 0
            else
                echo -e "${YELLOW}Fabric not detected${NC}"
                exit 1
            fi
            ;;
        quilt)
            if detect_quilt; then
                local version=$(get_quilt_version)
                echo -e "${GREEN}Quilt detected (version: $version)${NC}"
                exit 0
            else
                echo -e "${YELLOW}Quilt not detected${NC}"
                exit 1
            fi
            ;;
        list-mods)
            list_mods
            ;;
        help|*)
            echo -e "${BLUE}Mod Loader Detector${NC}"
            echo ""
            echo "Usage: $0 {detect|forge|fabric|quilt|list-mods|help}"
            echo ""
            echo "Commands:"
            echo "  detect      - Detect all installed mod loaders"
            echo "  forge       - Check for Forge"
            echo "  fabric      - Check for Fabric"
            echo "  quilt       - Check for Quilt"
            echo "  list-mods   - List installed mods"
            echo "  help        - Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0 detect"
            echo "  $0 forge"
            echo "  $0 list-mods"
            echo ""
            exit 1
            ;;
    esac
}

# Run main function
main "$@"

