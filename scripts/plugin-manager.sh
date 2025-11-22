#!/bin/bash
# Plugin Manager for Minecraft Server
# Handles plugin installation, updates, enable/disable, and configuration

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

# Plugin directories (check both locations)
PLUGIN_DIRS=("${PROJECT_DIR}/plugins" "${PROJECT_DIR}/data/plugins")
PLUGIN_DIR="${PROJECT_DIR}/plugins"
PLUGIN_CONFIG_DIR="${PROJECT_DIR}/data/plugins"
PLUGIN_BACKUP_DIR="${PROJECT_DIR}/backups/plugins"
PLUGIN_DISABLED_DIR="${PROJECT_DIR}/plugins/disabled"

# Ensure directories exist
mkdir -p "$PLUGIN_DIR" "$PLUGIN_CONFIG_DIR" "$PLUGIN_BACKUP_DIR" "$PLUGIN_DISABLED_DIR"

# Function to find plugin directory
find_plugin_dir() {
    for dir in "${PLUGIN_DIRS[@]}"; do
        if [ -d "$dir" ]; then
            echo "$dir"
            return 0
        fi
    done
    # Create default if none exist
    mkdir -p "$PLUGIN_DIR"
    echo "$PLUGIN_DIR"
}

# Function to get plugin info from jar
get_plugin_info() {
    local plugin_file="$1"

    if [ ! -f "$plugin_file" ]; then
        return 1
    fi

    # Try to extract plugin.yml or paper-plugin.yml
    local temp_dir=$(mktemp -d)
    unzip -q -o "$plugin_file" -d "$temp_dir" 2>/dev/null || return 1

    local plugin_yml=""
    if [ -f "$temp_dir/plugin.yml" ]; then
        plugin_yml="$temp_dir/plugin.yml"
    elif [ -f "$temp_dir/paper-plugin.yml" ]; then
        plugin_yml="$temp_dir/paper-plugin.yml"
    else
        rm -rf "$temp_dir"
        return 1
    fi

    # Extract plugin name and version
    local name=$(grep -E "^name:" "$plugin_yml" 2>/dev/null | cut -d: -f2 | tr -d ' ' | head -1)
    local version=$(grep -E "^version:" "$plugin_yml" 2>/dev/null | cut -d: -f2 | tr -d ' ' | head -1)
    local api_version=$(grep -E "^api-version:" "$plugin_yml" 2>/dev/null | cut -d: -f2 | tr -d ' ' | head -1)

    # Extract dependencies
    local dependencies=""
    if grep -qE "^depend:" "$plugin_yml" 2>/dev/null; then
        dependencies=$(grep -E "^depend:" "$plugin_yml" 2>/dev/null | cut -d: -f2 | tr -d ' ' | tr '\n' ',' | sed 's/,$//')
    elif grep -qE "^softdepend:" "$plugin_yml" 2>/dev/null; then
        dependencies=$(grep -E "^softdepend:" "$plugin_yml" 2>/dev/null | cut -d: -f2 | tr -d ' ' | tr '\n' ',' | sed 's/,$//')
    fi

    # Extract load order
    local load_before=""
    if grep -qE "^load:" "$plugin_yml" 2>/dev/null; then
        load_before=$(grep -E "^load:" "$plugin_yml" 2>/dev/null | cut -d: -f2 | tr -d ' ' | head -1)
    fi

    rm -rf "$temp_dir"

    echo "$name|$version|$api_version|$dependencies|$load_before"
}

# Function to check plugin compatibility
check_plugin_compatibility() {
    local plugin_file="$1"
    local server_type=${SERVER_TYPE:-vanilla}

    if [ ! -f "$plugin_file" ]; then
        return 1
    fi

    local plugin_info=$(get_plugin_info "$plugin_file" 2>/dev/null || echo "Unknown|Unknown|Unknown||")
    local api_version=$(echo "$plugin_info" | cut -d'|' -f3)

    # Check if server type supports plugins
    if [ "$server_type" = "vanilla" ]; then
        echo -e "${RED}Warning: Vanilla server does not support plugins${NC}"
        echo -e "${YELLOW}Switch to Paper or Spigot to use plugins${NC}"
        return 1
    fi

    # Check API version compatibility (basic check)
    if [ "$api_version" != "Unknown" ] && [ -n "$api_version" ]; then
        # Get current server version
        local current_version=$(grep -E "MINECRAFT_VERSION=" "${PROJECT_DIR}/docker-compose.yml" | head -1 | sed 's/.*MINECRAFT_VERSION:-\([^}]*\).*/\1/' | sed 's/.*MINECRAFT_VERSION=\([^}]*\).*/\1/' | tr -d '"' | tr -d "'" || echo "1.20.4")
        current_version=${current_version:-${MINECRAFT_VERSION:-1.20.4}}

        # Extract major.minor from versions
        local api_major=$(echo "$api_version" | cut -d'.' -f1)
        local api_minor=$(echo "$api_version" | cut -d'.' -f2)
        local server_major=$(echo "$current_version" | cut -d'.' -f1)
        local server_minor=$(echo "$current_version" | cut -d'.' -f2)

        # Basic compatibility check (same major version)
        if [ "$api_major" != "$server_major" ]; then
            echo -e "${YELLOW}Warning: API version mismatch (Plugin: $api_version, Server: $current_version)${NC}"
            echo -e "${YELLOW}Plugin may not work correctly${NC}"
            return 1
        fi
    fi

    return 0
}

# Function to check plugin dependencies
check_plugin_dependencies() {
    local plugin_file="$1"
    local plugin_dir=$(find_plugin_dir)

    if [ ! -f "$plugin_file" ]; then
        return 1
    fi

    local plugin_info=$(get_plugin_info "$plugin_file" 2>/dev/null || echo "Unknown|Unknown|Unknown||")
    local dependencies=$(echo "$plugin_info" | cut -d'|' -f4)

    if [ -z "$dependencies" ] || [ "$dependencies" = "Unknown" ]; then
        return 0  # No dependencies
    fi

    local missing_deps=()
    IFS=',' read -ra DEPS <<< "$dependencies"
    for dep in "${DEPS[@]}"; do
        dep=$(echo "$dep" | tr -d ' ')
        if [ -n "$dep" ]; then
            # Check if dependency is installed
            local found=false
            for plugin in "$plugin_dir"/*.jar; do
                if [ -f "$plugin" ]; then
                    local dep_info=$(get_plugin_info "$plugin" 2>/dev/null || echo "Unknown|Unknown|Unknown||")
                    local dep_name=$(echo "$dep_info" | cut -d'|' -f1)
                    if [ "$dep_name" = "$dep" ]; then
                        found=true
                        break
                    fi
                fi
            done

            if [ "$found" = false ]; then
                missing_deps+=("$dep")
            fi
        fi
    done

    if [ ${#missing_deps[@]} -gt 0 ]; then
        echo -e "${YELLOW}Warning: Missing dependencies:${NC}"
        for dep in "${missing_deps[@]}"; do
            echo -e "  - $dep"
        done
        echo -e "${YELLOW}Plugin may not work without these dependencies${NC}"
        return 1
    fi

    return 0
}

# Function to install plugin
install_plugin() {
    local plugin_file="$1"
    local plugin_dir=$(find_plugin_dir)

    if [ ! -f "$plugin_file" ]; then
        echo -e "${RED}Error: Plugin file not found: $plugin_file${NC}"
        return 1
    fi

    if [[ ! "$plugin_file" =~ \.jar$ ]]; then
        echo -e "${RED}Error: Plugin must be a .jar file${NC}"
        return 1
    fi

    # Check compatibility
    echo -e "${BLUE}Checking plugin compatibility...${NC}"
    if ! check_plugin_compatibility "$plugin_file"; then
        read -p "Continue anyway? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo -e "${YELLOW}Installation cancelled${NC}"
            return 1
        fi
    fi

    # Check dependencies
    echo -e "${BLUE}Checking plugin dependencies...${NC}"
    if ! check_plugin_dependencies "$plugin_file"; then
        read -p "Continue without dependencies? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo -e "${YELLOW}Installation cancelled${NC}"
            return 1
        fi
    fi

    local plugin_name=$(basename "$plugin_file")
    local dest_file="${plugin_dir}/${plugin_name}"

    # Check if plugin already exists
    if [ -f "$dest_file" ]; then
        echo -e "${YELLOW}Plugin already exists: $plugin_name${NC}"
        read -p "Overwrite? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo -e "${YELLOW}Installation cancelled${NC}"
            return 1
        fi
        # Backup existing plugin
        cp "$dest_file" "${PLUGIN_BACKUP_DIR}/${plugin_name}.backup.$(date +%Y%m%d_%H%M%S)"
    fi

    # Get plugin info
    local plugin_info=$(get_plugin_info "$plugin_file" 2>/dev/null || echo "Unknown|Unknown|Unknown|||")
    local name=$(echo "$plugin_info" | cut -d'|' -f1)
    local version=$(echo "$plugin_info" | cut -d'|' -f2)

    echo -e "${BLUE}Installing plugin: $name (v$version)${NC}"

    # Copy plugin
    cp "$plugin_file" "$dest_file"

    # Backup plugin configs if they exist
    if [ -d "${PLUGIN_CONFIG_DIR}/${name}" ]; then
        echo -e "${BLUE}Backing up existing plugin configuration...${NC}"
        mkdir -p "${PLUGIN_BACKUP_DIR}/configs/${name}"
        cp -r "${PLUGIN_CONFIG_DIR}/${name}" "${PLUGIN_BACKUP_DIR}/configs/${name}.backup.$(date +%Y%m%d_%H%M%S)"
    fi

    echo -e "${GREEN}Plugin installed: $plugin_name${NC}"
    echo -e "${YELLOW}Note: Restart server to load plugin${NC}"
}

# Function to list plugins
list_plugins() {
    local plugin_dir=$(find_plugin_dir)
    local disabled_dir="$PLUGIN_DISABLED_DIR"

    echo -e "${BLUE}Installed Plugins:${NC}"
    echo ""

    local count=0
    for plugin in "$plugin_dir"/*.jar; do
        if [ -f "$plugin" ]; then
            count=$((count + 1))
            local plugin_name=$(basename "$plugin")
            local plugin_info=$(get_plugin_info "$plugin" 2>/dev/null || echo "Unknown|Unknown|Unknown|||")
            local name=$(echo "$plugin_info" | cut -d'|' -f1)
            local version=$(echo "$plugin_info" | cut -d'|' -f2)

            if [ "$name" = "Unknown" ]; then
                name="$plugin_name"
            fi

            echo -e "  ${GREEN}✓${NC} $name (v$version) - $plugin_name"
        fi
    done

    if [ $count -eq 0 ]; then
        echo -e "  ${YELLOW}No plugins installed${NC}"
    else
        echo ""
        echo -e "${GREEN}Total: $count plugin(s)${NC}"
    fi

    # List disabled plugins
    local disabled_count=0
    if [ -d "$disabled_dir" ]; then
        for plugin in "$disabled_dir"/*.jar; do
            if [ -f "$plugin" ]; then
                disabled_count=$((disabled_count + 1))
            fi
        done

        if [ $disabled_count -gt 0 ]; then
            echo ""
            echo -e "${YELLOW}Disabled Plugins: $disabled_count${NC}"
        fi
    fi
}

# Function to enable plugin
enable_plugin() {
    local plugin_name="$1"
    local plugin_dir=$(find_plugin_dir)
    local disabled_dir="$PLUGIN_DISABLED_DIR"

    # Try to find in disabled directory
    local disabled_file="${disabled_dir}/${plugin_name}"
    if [ ! -f "$disabled_file" ]; then
        # Try with .jar extension
        disabled_file="${disabled_dir}/${plugin_name}.jar"
    fi

    if [ ! -f "$disabled_file" ]; then
        echo -e "${RED}Error: Plugin not found in disabled directory: $plugin_name${NC}"
        return 1
    fi

    local enabled_file="${plugin_dir}/$(basename "$disabled_file")"

    if [ -f "$enabled_file" ]; then
        echo -e "${YELLOW}Plugin already enabled: $(basename "$enabled_file")${NC}"
        return 1
    fi

    mv "$disabled_file" "$enabled_file"
    echo -e "${GREEN}Plugin enabled: $(basename "$enabled_file")${NC}"
    echo -e "${YELLOW}Note: Restart server to load plugin${NC}"
}

# Function to disable plugin
disable_plugin() {
    local plugin_name="$1"
    local plugin_dir=$(find_plugin_dir)
    local disabled_dir="$PLUGIN_DISABLED_DIR"

    # Try to find plugin
    local plugin_file="${plugin_dir}/${plugin_name}"
    if [ ! -f "$plugin_file" ]; then
        # Try with .jar extension
        plugin_file="${plugin_dir}/${plugin_name}.jar"
    fi

    if [ ! -f "$plugin_file" ]; then
        echo -e "${RED}Error: Plugin not found: $plugin_name${NC}"
        return 1
    fi

    local disabled_file="${disabled_dir}/$(basename "$plugin_file")"

    if [ -f "$disabled_file" ]; then
        echo -e "${YELLOW}Plugin already disabled${NC}"
        return 1
    fi

    mv "$plugin_file" "$disabled_file"
    echo -e "${GREEN}Plugin disabled: $(basename "$plugin_file")${NC}"
    echo -e "${YELLOW}Note: Restart server to apply changes${NC}"
}

# Function to remove plugin
remove_plugin() {
    local plugin_name="$1"
    local plugin_dir=$(find_plugin_dir)

    # Try to find plugin
    local plugin_file="${plugin_dir}/${plugin_name}"
    if [ ! -f "$plugin_file" ]; then
        plugin_file="${plugin_dir}/${plugin_name}.jar"
    fi

    # Also check disabled directory
    if [ ! -f "$plugin_file" ]; then
        plugin_file="${PLUGIN_DISABLED_DIR}/${plugin_name}"
        if [ ! -f "$plugin_file" ]; then
            plugin_file="${PLUGIN_DISABLED_DIR}/${plugin_name}.jar"
        fi
    fi

    if [ ! -f "$plugin_file" ]; then
        echo -e "${RED}Error: Plugin not found: $plugin_name${NC}"
        return 1
    fi

    local plugin_info=$(get_plugin_info "$plugin_file" 2>/dev/null || echo "Unknown|Unknown|Unknown|||")
    local name=$(echo "$plugin_info" | cut -d'|' -f1)

    echo -e "${YELLOW}Removing plugin: $name${NC}"
    read -p "Are you sure? This will also remove plugin configuration. (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}Removal cancelled${NC}"
        return 1
    fi

    # Backup before removal
    local backup_file="${PLUGIN_BACKUP_DIR}/$(basename "$plugin_file").removed.$(date +%Y%m%d_%H%M%S)"
    cp "$plugin_file" "$backup_file"

    # Remove plugin
    rm -f "$plugin_file"

    # Remove config if exists
    if [ "$name" != "Unknown" ] && [ -d "${PLUGIN_CONFIG_DIR}/${name}" ]; then
        echo -e "${YELLOW}Removing plugin configuration...${NC}"
        rm -rf "${PLUGIN_CONFIG_DIR}/${name}"
    fi

    echo -e "${GREEN}Plugin removed: $name${NC}"
}

# Function to check for plugin updates
check_plugin_updates() {
    local plugin_dir=$(find_plugin_dir)

    echo -e "${BLUE}Checking for plugin updates...${NC}"
    echo ""

    local update_count=0
    local checked_count=0

    for plugin_file in "$plugin_dir"/*.jar; do
        if [ -f "$plugin_file" ]; then
            checked_count=$((checked_count + 1))
            local plugin_info=$(get_plugin_info "$plugin_file" 2>/dev/null || echo "Unknown|Unknown|Unknown|||")
            local name=$(echo "$plugin_info" | cut -d'|' -f1)
            local version=$(echo "$plugin_info" | cut -d'|' -f2)

            if [ "$name" = "Unknown" ]; then
                name=$(basename "$plugin_file" .jar)
            fi

            # Try to check for updates (this is a placeholder - would need API integration)
            # For now, just show current version
            echo -e "  ${GREEN}✓${NC} $name: v$version (installed)"
            # In a real implementation, this would query SpigotMC/PaperMC APIs
        fi
    done

    if [ $checked_count -eq 0 ]; then
        echo -e "${YELLOW}No plugins installed${NC}"
    else
        echo ""
        echo -e "${BLUE}Checked $checked_count plugin(s)${NC}"
        echo -e "${YELLOW}Note: Automatic update checking requires API integration${NC}"
        echo -e "${YELLOW}For now, manually check plugin pages for updates${NC}"
    fi
}

# Function to update plugin
update_plugin() {
    local plugin_name="$1"
    local new_plugin_file="$2"
    local plugin_dir=$(find_plugin_dir)

    if [ -z "$new_plugin_file" ]; then
        echo -e "${RED}Error: New plugin file not specified${NC}"
        echo -e "${YELLOW}Usage: $0 update <plugin_name> <new_plugin_file>${NC}"
        return 1
    fi

    if [ ! -f "$new_plugin_file" ]; then
        echo -e "${RED}Error: New plugin file not found: $new_plugin_file${NC}"
        return 1
    fi

    # Check compatibility of new version
    echo -e "${BLUE}Checking new version compatibility...${NC}"
    if ! check_plugin_compatibility "$new_plugin_file"; then
        read -p "Continue anyway? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo -e "${YELLOW}Update cancelled${NC}"
            return 1
        fi
    fi

    # Find existing plugin
    local old_plugin_file="${plugin_dir}/${plugin_name}"
    if [ ! -f "$old_plugin_file" ]; then
        old_plugin_file="${plugin_dir}/${plugin_name}.jar"
    fi

    if [ ! -f "$old_plugin_file" ]; then
        echo -e "${RED}Error: Plugin not found: $plugin_name${NC}"
        return 1
    fi

    local old_info=$(get_plugin_info "$old_plugin_file" 2>/dev/null || echo "Unknown|Unknown|Unknown|||")
    local new_info=$(get_plugin_info "$new_plugin_file" 2>/dev/null || echo "Unknown|Unknown|Unknown|||")

    local old_name=$(echo "$old_info" | cut -d'|' -f1)
    local old_version=$(echo "$old_info" | cut -d'|' -f2)
    local new_name=$(echo "$new_info" | cut -d'|' -f1)
    local new_version=$(echo "$new_info" | cut -d'|' -f2)

    echo -e "${BLUE}Updating plugin: $old_name${NC}"
    echo -e "  Old version: $old_version"
    echo -e "  New version: $new_version"

    # Backup old plugin and configs
    echo -e "${BLUE}Backing up old plugin and configuration...${NC}"
    cp "$old_plugin_file" "${PLUGIN_BACKUP_DIR}/$(basename "$old_plugin_file").backup.$(date +%Y%m%d_%H%M%S)"

    if [ "$old_name" != "Unknown" ] && [ -d "${PLUGIN_CONFIG_DIR}/${old_name}" ]; then
        mkdir -p "${PLUGIN_BACKUP_DIR}/configs/${old_name}"
        cp -r "${PLUGIN_CONFIG_DIR}/${old_name}" "${PLUGIN_BACKUP_DIR}/configs/${old_name}.backup.$(date +%Y%m%d_%H%M%S)"
    fi

    # Replace plugin
    cp "$new_plugin_file" "$old_plugin_file"

    echo -e "${GREEN}Plugin updated: $old_name${NC}"
    echo -e "${YELLOW}Note: Restart server to load updated plugin${NC}"
    echo -e "${YELLOW}Note: Review configuration changes - old configs backed up${NC}"
}

# Function to backup plugin configs
backup_plugin_configs() {
    local plugin_dir=$(find_plugin_dir)

    echo -e "${BLUE}Backing up plugin configurations...${NC}"

    local backup_timestamp=$(date +%Y%m%d_%H%M%S)
    local backup_path="${PLUGIN_BACKUP_DIR}/configs.${backup_timestamp}"

    if [ -d "$PLUGIN_CONFIG_DIR" ] && [ -n "$(ls -A "$PLUGIN_CONFIG_DIR" 2>/dev/null)" ]; then
        mkdir -p "$backup_path"
        cp -r "$PLUGIN_CONFIG_DIR"/* "$backup_path/" 2>/dev/null || true
        echo -e "${GREEN}Plugin configurations backed up to: $backup_path${NC}"
    else
        echo -e "${YELLOW}No plugin configurations found${NC}"
    fi
}

# Function to restore plugin configs
restore_plugin_configs() {
    local backup_path="$1"

    if [ -z "$backup_path" ]; then
        echo -e "${RED}Error: Backup path not specified${NC}"
        echo -e "${YELLOW}Usage: $0 restore-configs <backup_path>${NC}"
        return 1
    fi

    if [ ! -d "$backup_path" ]; then
        echo -e "${RED}Error: Backup path not found: $backup_path${NC}"
        return 1
    fi

    echo -e "${BLUE}Restoring plugin configurations from: $backup_path${NC}"

    # Backup current configs first
    backup_plugin_configs

    # Restore
    cp -r "$backup_path"/* "$PLUGIN_CONFIG_DIR/" 2>/dev/null || true

    echo -e "${GREEN}Plugin configurations restored${NC}"
    echo -e "${YELLOW}Note: Restart server to apply changes${NC}"
}

# Function to check if server supports hot-reload
check_hot_reload_support() {
    local server_type=${SERVER_TYPE:-vanilla}

    # Paper and some Spigot forks support /reload
    if [ "$server_type" = "paper" ] || [ "$server_type" = "spigot" ]; then
        return 0
    fi

    return 1
}

# Function to hot-reload plugins (if supported)
hot_reload_plugins() {
    if ! check_hot_reload_support; then
        echo -e "${RED}Error: Hot-reload not supported on $SERVER_TYPE server${NC}"
        echo -e "${YELLOW}Use 'restart' command instead${NC}"
        return 1
    fi

    echo -e "${BLUE}Attempting to hot-reload plugins...${NC}"

    if docker ps | grep -q minecraft-server; then
        # Try to send reload command via Docker
        if docker exec minecraft-server rcon-cli reload 2>/dev/null; then
            echo -e "${GREEN}Plugins reloaded successfully${NC}"
            return 0
        elif docker exec minecraft-server bash -c "echo 'reload' > /proc/$(pgrep -f java)/fd/0" 2>/dev/null; then
            echo -e "${GREEN}Reload command sent${NC}"
            echo -e "${YELLOW}Note: Check server logs to confirm reload${NC}"
            return 0
        else
            echo -e "${YELLOW}Warning: Could not send reload command automatically${NC}"
            echo -e "${YELLOW}You may need to run '/reload' in the server console${NC}"
            return 1
        fi
    else
        echo -e "${RED}Error: Server is not running${NC}"
        return 1
    fi
}

# Function to display usage
usage() {
    echo -e "${BLUE}Plugin Manager for Minecraft Server${NC}"
    echo ""
    echo "Usage: $0 {install|list|enable|disable|remove|update|check-updates|reload|backup-configs|restore-configs} [options]"
    echo ""
    echo "Commands:"
    echo "  install <file>              - Install a plugin from .jar file"
    echo "  list                        - List all installed plugins"
    echo "  enable <plugin>             - Enable a disabled plugin"
    echo "  disable <plugin>           - Disable a plugin (moves to disabled/)"
    echo "  remove <plugin>             - Remove a plugin completely"
    echo "  update <plugin> <file>      - Update a plugin with new .jar file"
    echo "  check-updates               - Check for available plugin updates"
    echo "  reload                      - Hot-reload plugins (Paper/Spigot only)"
    echo "  backup-configs               - Backup all plugin configurations"
    echo "  restore-configs <path>      - Restore plugin configurations from backup"
    echo ""
    exit 1
}

# Main function
main() {
    case "${1}" in
        install)
            if [ -z "$2" ]; then
                echo -e "${RED}Error: Plugin file not specified${NC}"
                usage
            fi
            install_plugin "$2"
            ;;
        list)
            list_plugins
            ;;
        enable)
            if [ -z "$2" ]; then
                echo -e "${RED}Error: Plugin name not specified${NC}"
                usage
            fi
            enable_plugin "$2"
            ;;
        disable)
            if [ -z "$2" ]; then
                echo -e "${RED}Error: Plugin name not specified${NC}"
                usage
            fi
            disable_plugin "$2"
            ;;
        remove)
            if [ -z "$2" ]; then
                echo -e "${RED}Error: Plugin name not specified${NC}"
                usage
            fi
            remove_plugin "$2"
            ;;
        update)
            if [ -z "$2" ] || [ -z "$3" ]; then
                echo -e "${RED}Error: Plugin name and new file required${NC}"
                usage
            fi
            update_plugin "$2" "$3"
            ;;
        check-updates)
            check_plugin_updates
            ;;
        reload)
            hot_reload_plugins
            ;;
        backup-configs)
            backup_plugin_configs
            ;;
        restore-configs)
            restore_plugin_configs "$2"
            ;;
        *)
            usage
            ;;
    esac
}

# Run main function
main "$@"

