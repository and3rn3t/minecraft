#!/bin/bash
# Server Properties Manager
# Manages server.properties with validation and presets

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
SERVER_PROPERTIES="${SERVER_PROPERTIES:-${PROJECT_DIR}/data/server.properties}"

# Property validation rules
declare -A PROPERTY_TYPES
declare -A PROPERTY_MIN
declare -A PROPERTY_MAX
declare -A PROPERTY_VALUES

# Integer properties with min/max
PROPERTY_MIN[max-players]=1
PROPERTY_MAX[max-players]=2147483647
PROPERTY_MIN[view-distance]=3
PROPERTY_MAX[view-distance]=32
PROPERTY_MIN[simulation-distance]=3
PROPERTY_MAX[simulation-distance]=32
PROPERTY_MIN[server-port]=1
PROPERTY_MAX[server-port]=65535
PROPERTY_MIN[spawn-protection]=0
PROPERTY_MAX[spawn-protection]=2147483647
PROPERTY_MIN[max-world-size]=1
PROPERTY_MAX[max-world-size]=29999984
PROPERTY_MIN[network-compression-threshold]=-1
PROPERTY_MAX[network-compression-threshold]=2147483647
PROPERTY_MIN[max-tick-time]=0
PROPERTY_MAX[max-tick-time]=2147483647

# Enum properties
PROPERTY_VALUES[difficulty]="peaceful,easy,normal,hard"
PROPERTY_VALUES[gamemode]="survival,creative,adventure,spectator"
PROPERTY_VALUES[level-type]="default,flat,largeBiomes,amplified,default_1_1"
PROPERTY_VALUES[online-mode]="true,false"
PROPERTY_VALUES[pvp]="true,false"
PROPERTY_VALUES[white-list]="true,false"
PROPERTY_VALUES[enforce-whitelist]="true,false"
PROPERTY_VALUES[enforce-secure-profile]="true,false"
PROPERTY_VALUES[spawn-monsters]="true,false"
PROPERTY_VALUES[spawn-npcs]="true,false"
PROPERTY_VALUES[spawn-animals]="true,false"
PROPERTY_VALUES[allow-flight]="true,false"
PROPERTY_VALUES[enable-command-block]="true,false"
PROPERTY_VALUES[enable-rcon]="true,false"
PROPERTY_VALUES[enable-query]="true,false"

# Function to backup server.properties
backup_properties() {
    local backup_file="${SERVER_PROPERTIES}.backup.$(date +%Y%m%d_%H%M%S)"
    if [ -f "$SERVER_PROPERTIES" ]; then
        cp "$SERVER_PROPERTIES" "$backup_file"
        echo -e "${GREEN}Backup created: $(basename "$backup_file")${NC}"
    fi
}

# Function to get property value
get_property() {
    local key="$1"
    if [ ! -f "$SERVER_PROPERTIES" ]; then
        echo -e "${RED}Error: server.properties not found${NC}"
        return 1
    fi

    # Get value, handling comments and empty lines
    local value=$(grep -E "^${key}=" "$SERVER_PROPERTIES" 2>/dev/null | cut -d'=' -f2- | head -1)

    if [ -z "$value" ]; then
        echo -e "${YELLOW}Property not found: $key${NC}"
        return 1
    fi

    echo "$value"
    return 0
}

# Function to set property value
set_property() {
    local key="$1"
    local value="$2"
    local validate="${3:-true}"

    if [ ! -f "$SERVER_PROPERTIES" ]; then
        echo -e "${RED}Error: server.properties not found${NC}"
        return 1
    fi

    # Validate property
    if [ "$validate" = "true" ]; then
        if ! validate_property "$key" "$value"; then
            return 1
        fi
    fi

    # Backup before changes
    backup_properties >/dev/null 2>&1

    # Check if property exists
    if grep -qE "^${key}=" "$SERVER_PROPERTIES" 2>/dev/null; then
        # Update existing property
        if [[ "$OSTYPE" == "darwin"* ]]; then
            sed -i '' "s|^${key}=.*|${key}=${value}|" "$SERVER_PROPERTIES"
        else
            sed -i "s|^${key}=.*|${key}=${value}|" "$SERVER_PROPERTIES"
        fi
    else
        # Add new property
        echo "${key}=${value}" >> "$SERVER_PROPERTIES"
    fi

    echo -e "${GREEN}✓ Property set: ${key}=${value}${NC}"
    return 0
}

# Function to validate property value
validate_property() {
    local key="$1"
    local value="$2"

    # Check if it's an enum property
    if [ -n "${PROPERTY_VALUES[$key]}" ]; then
        local valid_values="${PROPERTY_VALUES[$key]}"
        if echo "$valid_values" | grep -qE "(^|,)$value(,|$)"; then
            return 0
        else
            echo -e "${RED}Error: Invalid value for $key. Valid values: $valid_values${NC}"
            return 1
        fi
    fi

    # Check if it's an integer property
    if [ -n "${PROPERTY_MIN[$key]}" ] && [ -n "${PROPERTY_MAX[$key]}" ]; then
        if ! [[ "$value" =~ ^-?[0-9]+$ ]]; then
            echo -e "${RED}Error: $key must be an integer${NC}"
            return 1
        fi

        local min="${PROPERTY_MIN[$key]}"
        local max="${PROPERTY_MAX[$key]}"

        if [ "$value" -lt "$min" ] || [ "$value" -gt "$max" ]; then
            echo -e "${RED}Error: $key must be between $min and $max${NC}"
            return 1
        fi
    fi

    return 0
}

# Function to list all properties
list_properties() {
    if [ ! -f "$SERVER_PROPERTIES" ]; then
        echo -e "${RED}Error: server.properties not found${NC}"
        return 1
    fi

    echo -e "${BLUE}Server Properties:${NC}"
    echo ""

    # List non-comment properties
    grep -vE "^#|^$" "$SERVER_PROPERTIES" | while IFS='=' read -r key value; do
        echo "  ${key}=${value}"
    done
}

# Function to apply performance preset
apply_preset() {
    local preset="$1"

    case "$preset" in
        low-end|performance)
            echo -e "${BLUE}Applying Low-End Performance Preset...${NC}"
            set_property "view-distance" "6" false
            set_property "simulation-distance" "4" false
            set_property "max-players" "5" false
            set_property "network-compression-threshold" "128" false
            set_property "entity-broadcast-range-percentage" "50" false
            set_property "max-tick-time" "60000" false
            echo -e "${GREEN}✓ Low-End preset applied${NC}"
            ;;
        balanced)
            echo -e "${BLUE}Applying Balanced Preset...${NC}"
            set_property "view-distance" "10" false
            set_property "simulation-distance" "8" false
            set_property "max-players" "10" false
            set_property "network-compression-threshold" "256" false
            set_property "entity-broadcast-range-percentage" "100" false
            echo -e "${GREEN}✓ Balanced preset applied${NC}"
            ;;
        high-performance|high)
            echo -e "${BLUE}Applying High-Performance Preset...${NC}"
            set_property "view-distance" "12" false
            set_property "simulation-distance" "10" false
            set_property "max-players" "20" false
            set_property "network-compression-threshold" "512" false
            set_property "entity-broadcast-range-percentage" "100" false
            echo -e "${GREEN}✓ High-Performance preset applied${NC}"
            ;;
        *)
            echo -e "${RED}Error: Unknown preset: $preset${NC}"
            echo "Available presets: low-end, balanced, high-performance"
            return 1
            ;;
    esac
}

# Function to show property info
show_property_info() {
    local key="$1"

    echo -e "${BLUE}Property: $key${NC}"
    echo ""

    # Get current value
    local current=$(get_property "$key" 2>/dev/null || echo "not set")
    echo "  Current value: $current"

    # Show validation rules
    if [ -n "${PROPERTY_VALUES[$key]}" ]; then
        echo "  Valid values: ${PROPERTY_VALUES[$key]}"
    elif [ -n "${PROPERTY_MIN[$key]}" ] && [ -n "${PROPERTY_MAX[$key]}" ]; then
        echo "  Range: ${PROPERTY_MIN[$key]} - ${PROPERTY_MAX[$key]}"
    fi
}

# Main function
main() {
    local command="${1:-help}"

    case "$command" in
        get)
            if [ -z "$2" ]; then
                echo -e "${RED}Error: Property key required${NC}"
                exit 1
            fi
            get_property "$2"
            ;;
        set)
            if [ -z "$2" ] || [ -z "$3" ]; then
                echo -e "${RED}Error: Property key and value required${NC}"
                echo "Usage: $0 set <key> <value>"
                exit 1
            fi
            set_property "$2" "$3"
            ;;
        list)
            list_properties
            ;;
        preset)
            if [ -z "$2" ]; then
                echo -e "${RED}Error: Preset name required${NC}"
                echo "Available presets: low-end, balanced, high-performance"
                exit 1
            fi
            apply_preset "$2"
            ;;
        info)
            if [ -z "$2" ]; then
                echo -e "${RED}Error: Property key required${NC}"
                exit 1
            fi
            show_property_info "$2"
            ;;
        backup)
            backup_properties
            ;;
        help|*)
            echo -e "${BLUE}Server Properties Manager${NC}"
            echo ""
            echo "Usage: $0 {command} [options]"
            echo ""
            echo "Commands:"
            echo "  get <key>              - Get property value"
            echo "  set <key> <value>     - Set property value"
            echo "  list                   - List all properties"
            echo "  preset <name>         - Apply performance preset"
            echo "  info <key>            - Show property information"
            echo "  backup                 - Backup server.properties"
            echo "  help                   - Show this help message"
            echo ""
            echo "Presets:"
            echo "  low-end               - Low-end performance (4GB Pi)"
            echo "  balanced              - Balanced performance (8GB Pi)"
            echo "  high-performance      - High performance settings"
            echo ""
            echo "Examples:"
            echo "  $0 get view-distance"
            echo "  $0 set view-distance 10"
            echo "  $0 preset balanced"
            echo "  $0 info max-players"
            echo ""
            exit 1
            ;;
    esac
}

# Run main function
main "$@"

