#!/bin/bash
# World Manager for Minecraft Server
# Handles multiple world creation, deletion, switching, and management

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
WORLDS_DIR="${DATA_DIR}"
SERVER_PROPERTIES="${PROJECT_DIR}/server.properties"
WORLD_CONFIG_DIR="${PROJECT_DIR}/config/worlds"
WORLD_TEMPLATES_DIR="${PROJECT_DIR}/config/world-templates"

# Ensure directories exist
mkdir -p "$WORLD_CONFIG_DIR" "$WORLD_TEMPLATES_DIR"

# Function to get current world name
get_current_world() {
    if [ -f "$SERVER_PROPERTIES" ]; then
        grep -E "^level-name=" "$SERVER_PROPERTIES" | cut -d'=' -f2 | tr -d '\r' || echo "world"
    else
        echo "world"
    fi
}

# Function to list all worlds
list_worlds() {
    echo -e "${BLUE}Available Worlds:${NC}"
    echo ""

    local current_world=$(get_current_world)
    local count=0

    # Find all world directories
    for world_dir in "$WORLDS_DIR"/world*; do
        if [ -d "$world_dir" ] && [ -f "${world_dir}/level.dat" ]; then
            count=$((count + 1))
            local world_name=$(basename "$world_dir")
            local world_size=$(du -sh "$world_dir" 2>/dev/null | cut -f1)
            local world_type="Unknown"

            # Try to determine world type from level.dat or region files
            if [ -d "${world_dir}/region" ]; then
                world_type="Overworld"
            elif [ -d "${world_dir}/DIM-1" ]; then
                world_type="Nether"
            elif [ -d "${world_dir}/DIM1" ]; then
                world_type="End"
            fi

            if [ "$world_name" = "$current_world" ]; then
                echo -e "  ${GREEN}✓${NC} ${GREEN}[ACTIVE]${NC} $world_name ($world_size) - $world_type"
            else
                echo -e "  ${BLUE}○${NC} $world_name ($world_size) - $world_type"
            fi
        fi
    done

    if [ $count -eq 0 ]; then
        echo -e "  ${YELLOW}No worlds found${NC}"
    else
        echo ""
        echo -e "${GREEN}Total: $count world(s)${NC}"
        echo -e "${BLUE}Current world: $current_world${NC}"
    fi
}

# Function to create a new world
create_world() {
    local world_name="$1"
    local world_type="${2:-normal}"
    local seed="${3:-}"

    if [ -z "$world_name" ]; then
        echo -e "${RED}Error: World name not specified${NC}"
        echo -e "${YELLOW}Usage: $0 create <world-name> [type] [seed]${NC}"
        return 1
    fi

    # Validate world name (alphanumeric and underscores only)
    if [[ ! "$world_name" =~ ^[a-zA-Z0-9_]+$ ]]; then
        echo -e "${RED}Error: World name must contain only letters, numbers, and underscores${NC}"
        return 1
    fi

    local world_path="${WORLDS_DIR}/${world_name}"

    # Check if world already exists
    if [ -d "$world_path" ] && [ -f "${world_path}/level.dat" ]; then
        echo -e "${YELLOW}World already exists: $world_name${NC}"
        read -p "Overwrite? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo -e "${YELLOW}Creation cancelled${NC}"
            return 1
        fi
        # Backup existing world
        if [ -d "$world_path" ]; then
            local backup_name="${world_name}.backup.$(date +%Y%m%d_%H%M%S)"
            mv "$world_path" "${WORLDS_DIR}/${backup_name}"
            echo -e "${BLUE}Existing world backed up to: $backup_name${NC}"
        fi
    fi

    echo -e "${BLUE}Creating new world: $world_name${NC}"
    echo -e "  Type: $world_type"
    if [ -n "$seed" ]; then
        echo -e "  Seed: $seed"
    fi

    # Check if server is running
    local server_running=false
    if docker ps | grep -q minecraft-server; then
        server_running=true
        echo -e "${YELLOW}Server is running. World will be created on next start.${NC}"
        echo -e "${YELLOW}Or stop server to create world immediately.${NC}"
    fi

    # Create world directory
    mkdir -p "$world_path"

    # Create world configuration
    local world_config="${WORLD_CONFIG_DIR}/${world_name}.conf"
    cat > "$world_config" <<EOF
# World configuration for $world_name
WORLD_NAME=$world_name
WORLD_TYPE=$world_type
WORLD_SEED=$seed
CREATED=$(date +%Y-%m-%d\ %H:%M:%S)
EOF

    if [ "$server_running" = false ]; then
        # If server is not running, we can prepare the world
        # But actual world generation happens when server starts
        echo -e "${GREEN}World directory created: $world_path${NC}"
        echo -e "${YELLOW}World will be generated when server starts with this world${NC}"
    fi

    echo -e "${GREEN}World created: $world_name${NC}"
    echo -e "${YELLOW}Note: Switch to this world and start server to generate it${NC}"
}

# Function to delete a world
delete_world() {
    local world_name="$1"

    if [ -z "$world_name" ]; then
        echo -e "${RED}Error: World name not specified${NC}"
        echo -e "${YELLOW}Usage: $0 delete <world-name>${NC}"
        return 1
    fi

    local current_world=$(get_current_world)

    if [ "$world_name" = "$current_world" ]; then
        echo -e "${RED}Error: Cannot delete the active world: $world_name${NC}"
        echo -e "${YELLOW}Switch to another world first${NC}"
        return 1
    fi

    local world_path="${WORLDS_DIR}/${world_name}"

    if [ ! -d "$world_path" ] || [ ! -f "${world_path}/level.dat" ]; then
        echo -e "${RED}Error: World not found: $world_name${NC}"
        return 1
    fi

    # Get world size for confirmation
    local world_size=$(du -sh "$world_path" 2>/dev/null | cut -f1)

    echo -e "${YELLOW}Warning: This will permanently delete world: $world_name${NC}"
    echo -e "  Size: $world_size"
    read -p "Are you sure? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}Deletion cancelled${NC}"
        return 1
    fi

    # Backup before deletion
    local backup_name="${world_name}.deleted.$(date +%Y%m%d_%H%M%S)"
    echo -e "${BLUE}Creating backup before deletion...${NC}"
    tar -czf "${PROJECT_DIR}/backups/${backup_name}.tar.gz" -C "$WORLDS_DIR" "$world_name" 2>/dev/null || true

    # Delete world
    rm -rf "$world_path"

    # Delete world configuration
    rm -f "${WORLD_CONFIG_DIR}/${world_name}.conf"

    echo -e "${GREEN}World deleted: $world_name${NC}"
    echo -e "${BLUE}Backup saved to: backups/${backup_name}.tar.gz${NC}"
}

# Function to switch to a different world
switch_world() {
    local world_name="$1"

    if [ -z "$world_name" ]; then
        echo -e "${RED}Error: World name not specified${NC}"
        echo -e "${YELLOW}Usage: $0 switch <world-name>${NC}"
        return 1
    fi

    local current_world=$(get_current_world)

    if [ "$world_name" = "$current_world" ]; then
        echo -e "${GREEN}Already using world: $world_name${NC}"
        return 0
    fi

    local world_path="${WORLDS_DIR}/${world_name}"

    # Check if world exists (or will be created)
    if [ ! -d "$world_path" ]; then
        echo -e "${YELLOW}World directory doesn't exist: $world_name${NC}"
        read -p "Create new world? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            create_world "$world_name"
        else
            echo -e "${YELLOW}Switch cancelled${NC}"
            return 1
        fi
    fi

    # Check if server is running
    if docker ps | grep -q minecraft-server; then
        echo -e "${YELLOW}Server is running. Stopping to switch worlds...${NC}"
        cd "$PROJECT_DIR"
        ./scripts/manage.sh stop
    fi

    # Update server.properties
    if [ -f "$SERVER_PROPERTIES" ]; then
        # Backup server.properties
        cp "$SERVER_PROPERTIES" "${SERVER_PROPERTIES}.bak"

        # Update level-name
        if grep -q "^level-name=" "$SERVER_PROPERTIES"; then
            sed -i.bak "s/^level-name=.*/level-name=$world_name/" "$SERVER_PROPERTIES"
        else
            echo "level-name=$world_name" >> "$SERVER_PROPERTIES"
        fi

        rm -f "${SERVER_PROPERTIES}.bak"

        # Apply world-specific configuration
        apply_world_config "$world_name"

        echo -e "${GREEN}Switched to world: $world_name${NC}"
        echo -e "${YELLOW}Note: Start server to load the new world${NC}"
    else
        echo -e "${RED}Error: server.properties not found${NC}"
        return 1
    fi
}

# Function to get world information
world_info() {
    local world_name="$1"

    if [ -z "$world_name" ]; then
        world_name=$(get_current_world)
    fi

    local world_path="${WORLDS_DIR}/${world_name}"

    if [ ! -d "$world_path" ] || [ ! -f "${world_path}/level.dat" ]; then
        echo -e "${RED}Error: World not found: $world_name${NC}"
        return 1
    fi

    echo -e "${BLUE}World Information: $world_name${NC}"
    echo "=================="

    # World size
    local world_size=$(du -sh "$world_path" 2>/dev/null | cut -f1)
    echo "Size: $world_size"

    # World type
    if [ -d "${world_path}/region" ]; then
        echo "Type: Overworld"
        local region_count=$(find "${world_path}/region" -name "*.mca" 2>/dev/null | wc -l)
        echo "Regions: $region_count"
    fi

    # Check for dimensions
    if [ -d "${world_path}/DIM-1" ]; then
        echo "Nether: Yes"
    fi
    if [ -d "${world_path}/DIM1" ]; then
        echo "End: Yes"
    fi

    # World configuration
    local world_config="${WORLD_CONFIG_DIR}/${world_name}.conf"
    if [ -f "$world_config" ]; then
        echo ""
        echo "Configuration:"
        cat "$world_config" | grep -v "^#" | while IFS='=' read -r key value; do
            if [ -n "$key" ] && [ -n "$value" ]; then
                echo "  $key: $value"
            fi
        done
    fi

    # Check if active
    local current_world=$(get_current_world)
    if [ "$world_name" = "$current_world" ]; then
        echo ""
        echo -e "${GREEN}Status: ACTIVE${NC}"
    fi
}

# Function to backup a specific world
backup_world() {
    local world_name="$1"

    if [ -z "$world_name" ]; then
        world_name=$(get_current_world)
    fi

    local world_path="${WORLDS_DIR}/${world_name}"

    if [ ! -d "$world_path" ] || [ ! -f "${world_path}/level.dat" ]; then
        echo -e "${RED}Error: World not found: $world_name${NC}"
        return 1
    fi

    echo -e "${BLUE}Backing up world: $world_name${NC}"

    # Use the main backup script but target specific world
    cd "$PROJECT_DIR"
    if [ -f "${SCRIPT_DIR}/manage.sh" ]; then
        # Create a temporary backup focusing on this world
        local backup_file="${PROJECT_DIR}/backups/world_${world_name}_$(date +%Y%m%d_%H%M%S).tar.gz"
        tar -czf "$backup_file" -C "$WORLDS_DIR" "$world_name"

        if [ $? -eq 0 ]; then
            local backup_size=$(du -sh "$backup_file" 2>/dev/null | cut -f1)
            echo -e "${GREEN}World backed up: $backup_file ($backup_size)${NC}"
        else
            echo -e "${RED}Backup failed${NC}"
            return 1
        fi
    else
        echo -e "${RED}Error: manage.sh not found${NC}"
        return 1
    fi
}

# Function to get world size in bytes
get_world_size_bytes() {
    local world_name="$1"
    local world_path="${WORLDS_DIR}/${world_name}"

    if [ -d "$world_path" ]; then
        du -sb "$world_path" 2>/dev/null | cut -f1 || echo "0"
    else
        echo "0"
    fi
}

# Function to monitor world sizes
monitor_world_sizes() {
    echo -e "${BLUE}World Size Monitoring${NC}"
    echo "===================="
    echo ""

    local total_size=0
    local count=0

    for world_dir in "$WORLDS_DIR"/world*; do
        if [ -d "$world_dir" ] && [ -f "${world_dir}/level.dat" ]; then
            count=$((count + 1))
            local world_name=$(basename "$world_dir")
            local world_size=$(du -sh "$world_dir" 2>/dev/null | cut -f1)
            local world_size_bytes=$(get_world_size_bytes "$world_name")
            total_size=$((total_size + world_size_bytes))

            # Format size in human-readable format
            local size_mb=$((world_size_bytes / 1024 / 1024))
            local size_gb=$((size_mb / 1024))

            if [ $size_gb -gt 0 ]; then
                local size_display="${size_gb}.$((size_mb % 1024 / 100))GB"
            else
                local size_display="${size_mb}MB"
            fi

            echo -e "  ${GREEN}$world_name${NC}: $world_size ($size_display)"
        fi
    done

    if [ $count -eq 0 ]; then
        echo -e "  ${YELLOW}No worlds found${NC}"
    else
        echo ""
        local total_mb=$((total_size / 1024 / 1024))
        local total_gb=$((total_mb / 1024))
        if [ $total_gb -gt 0 ]; then
            local total_display="${total_gb}.$((total_mb % 1024 / 100))GB"
        else
            local total_display="${total_mb}MB"
        fi
        echo -e "${GREEN}Total: $count world(s), $total_display${NC}"
    fi
}

# Function to apply per-world configuration
apply_world_config() {
    local world_name="$1"

    if [ -z "$world_name" ]; then
        world_name=$(get_current_world)
    fi

    local world_config="${WORLD_CONFIG_DIR}/${world_name}.conf"

    if [ ! -f "$world_config" ]; then
        echo -e "${YELLOW}No configuration found for world: $world_name${NC}"
        echo -e "${BLUE}Creating default configuration...${NC}"
        create_world "$world_name" "normal" ""
        world_config="${WORLD_CONFIG_DIR}/${world_name}.conf"
    fi

    # Source the world configuration
    if [ -f "$world_config" ]; then
        source "$world_config"

        # Apply world-specific server.properties settings if they exist
        if [ -f "$SERVER_PROPERTIES" ]; then
            # Backup server.properties
            cp "$SERVER_PROPERTIES" "${SERVER_PROPERTIES}.bak"

            # Apply world type
            if [ -n "$WORLD_TYPE" ]; then
                case "$WORLD_TYPE" in
                    flat)
                        sed -i.bak "s/^level-type=.*/level-type=minecraft\\:flat/" "$SERVER_PROPERTIES"
                        ;;
                    amplified)
                        sed -i.bak "s/^level-type=.*/level-type=minecraft\\:amplified/" "$SERVER_PROPERTIES"
                        ;;
                    large_biomes)
                        sed -i.bak "s/^level-type=.*/level-type=minecraft\\:large_biomes/" "$SERVER_PROPERTIES"
                        ;;
                    normal|*)
                        sed -i.bak "s/^level-type=.*/level-type=minecraft\\:normal/" "$SERVER_PROPERTIES"
                        ;;
                esac
            fi

            # Apply seed if specified
            if [ -n "$WORLD_SEED" ] && [ "$WORLD_SEED" != "" ]; then
                if grep -q "^level-seed=" "$SERVER_PROPERTIES"; then
                    sed -i.bak "s/^level-seed=.*/level-seed=$WORLD_SEED/" "$SERVER_PROPERTIES"
                else
                    echo "level-seed=$WORLD_SEED" >> "$SERVER_PROPERTIES"
                fi
            fi

            rm -f "${SERVER_PROPERTIES}.bak"
            echo -e "${GREEN}World configuration applied: $world_name${NC}"
        fi
    fi
}

# Function to create world template
create_world_template() {
    local template_name="$1"
    local source_world="$2"

    if [ -z "$template_name" ]; then
        echo -e "${RED}Error: Template name not specified${NC}"
        echo -e "${YELLOW}Usage: $0 create-template <template-name> [source-world]${NC}"
        return 1
    fi

    if [ -z "$source_world" ]; then
        source_world=$(get_current_world)
    fi

    local source_path="${WORLDS_DIR}/${source_world}"
    local template_path="${WORLD_TEMPLATES_DIR}/${template_name}"

    if [ ! -d "$source_path" ] || [ ! -f "${source_path}/level.dat" ]; then
        echo -e "${RED}Error: Source world not found: $source_world${NC}"
        return 1
    fi

    echo -e "${BLUE}Creating world template: $template_name${NC}"
    echo -e "  Source: $source_world"

    # Create template directory
    mkdir -p "$template_path"

    # Copy world files (excluding player data and logs)
    echo -e "${BLUE}Copying world data...${NC}"
    rsync -a --exclude='playerdata' --exclude='stats' --exclude='advancements' \
          --exclude='*.log' --exclude='logs' \
          "$source_path/" "$template_path/" 2>/dev/null || {
        # Fallback to tar if rsync not available
        tar -czf "${template_path}/world.tar.gz" -C "$WORLDS_DIR" "$source_world" --exclude='playerdata' --exclude='stats' --exclude='advancements' 2>/dev/null
    }

    # Copy world configuration
    local source_config="${WORLD_CONFIG_DIR}/${source_world}.conf"
    if [ -f "$source_config" ]; then
        cp "$source_config" "${template_path}/world.conf"
    fi

    echo -e "${GREEN}Template created: $template_name${NC}"
    echo -e "${YELLOW}Note: Template can be used to create new worlds${NC}"
}

# Function to create world from template
create_from_template() {
    local world_name="$1"
    local template_name="$2"

    if [ -z "$world_name" ] || [ -z "$template_name" ]; then
        echo -e "${RED}Error: World name and template name required${NC}"
        echo -e "${YELLOW}Usage: $0 from-template <world-name> <template-name>${NC}"
        return 1
    fi

    local template_path="${WORLD_TEMPLATES_DIR}/${template_name}"
    local world_path="${WORLDS_DIR}/${world_name}"

    if [ ! -d "$template_path" ]; then
        echo -e "${RED}Error: Template not found: $template_name${NC}"
        return 1
    fi

    if [ -d "$world_path" ] && [ -f "${world_path}/level.dat" ]; then
        echo -e "${YELLOW}World already exists: $world_name${NC}"
        read -p "Overwrite? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo -e "${YELLOW}Creation cancelled${NC}"
            return 1
        fi
        rm -rf "$world_path"
    fi

    echo -e "${BLUE}Creating world from template: $world_name${NC}"
    echo -e "  Template: $template_name"

    # Extract template
    if [ -f "${template_path}/world.tar.gz" ]; then
        mkdir -p "$world_path"
        tar -xzf "${template_path}/world.tar.gz" -C "$world_path" --strip-components=1
    elif [ -d "$template_path" ] && [ -f "${template_path}/level.dat" ]; then
        cp -r "$template_path" "$world_path"
        # Remove template-specific files
        rm -rf "${world_path}/playerdata" "${world_path}/stats" "${world_path}/advancements" 2>/dev/null || true
    else
        echo -e "${RED}Error: Invalid template format${NC}"
        return 1
    fi

    # Copy template configuration
    if [ -f "${template_path}/world.conf" ]; then
        cp "${template_path}/world.conf" "${WORLD_CONFIG_DIR}/${world_name}.conf"
        # Update world name in config
        sed -i.bak "s/WORLD_NAME=.*/WORLD_NAME=$world_name/" "${WORLD_CONFIG_DIR}/${world_name}.conf"
        rm -f "${WORLD_CONFIG_DIR}/${world_name}.conf.bak"
    fi

    echo -e "${GREEN}World created from template: $world_name${NC}"
}

# Function to display usage
usage() {
    echo -e "${BLUE}World Manager for Minecraft Server${NC}"
    echo ""
    echo "Usage: $0 {list|create|delete|switch|info|backup|sizes|config|create-template|from-template} [options]"
    echo ""
    echo "Commands:"
    echo "  list                        - List all available worlds"
    echo "  create <name> [type] [seed] - Create a new world"
    echo "  delete <name>               - Delete a world (with backup)"
    echo "  switch <name>               - Switch to a different world"
    echo "  info [name]                 - Show world information"
    echo "  backup [name]               - Backup a specific world"
    echo "  sizes                       - Monitor world sizes"
    echo "  config [name]               - Apply world-specific configuration"
    echo "  create-template <name> [world] - Create a world template"
    echo "  from-template <name> <template> - Create world from template"
    echo ""
    echo "World Types:"
    echo "  normal    - Standard world (default)"
    echo "  flat      - Superflat world"
    echo "  amplified - Amplified terrain"
    echo "  large_biomes - Large biomes"
    echo ""
    exit 1
}

# Main function
main() {
    case "${1:-}" in
        list)
            list_worlds
            ;;
        create)
            create_world "$2" "$3" "$4"
            ;;
        delete)
            delete_world "$2"
            ;;
        switch)
            switch_world "$2"
            ;;
        info)
            world_info "$2"
            ;;
        backup)
            backup_world "$2"
            ;;
        sizes)
            monitor_world_sizes
            ;;
        config)
            apply_world_config "$2"
            ;;
        create-template)
            create_world_template "$2" "$3"
            ;;
        from-template)
            create_from_template "$2" "$3"
            ;;
        *)
            usage
            ;;
    esac
}

# Run main function
main "$@"

