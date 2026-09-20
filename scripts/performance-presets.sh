#!/bin/bash
# Performance Presets Manager
# Applies pre-configured performance profiles

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
ENV_FILE="${ENV_FILE:-${PROJECT_DIR}/.env}"

# Memory is read from .env, not docker-compose.yml itself (Docker Compose
# loads .env automatically); docker-compose.yml only references the vars.
set_env_var() {
    local key="$1" value="$2"
    [ -f "$ENV_FILE" ] || touch "$ENV_FILE"
    if grep -q "^${key}=" "$ENV_FILE" 2>/dev/null; then
        sed -i.bak "s/^${key}=.*/${key}=${value}/" "$ENV_FILE"
        rm -f "${ENV_FILE}.bak"
    else
        echo "${key}=${value}" >> "$ENV_FILE"
    fi
}

# Prints the key's value from .env, or "key=default (default)" when .env is
# absent or doesn't set it — .env missing is a valid state (docker-compose.yml
# falls back to its own defaults), so "current" should never go silent on it.
show_env_or_default() {
    local key="$1" default="$2" line
    line="$(grep "^${key}=" "$ENV_FILE" 2>/dev/null || true)"
    if [ -n "$line" ]; then
        echo "  $line"
    else
        echo "  ${key}=${default} (default)"
    fi
}

# Converts a "9G"/"512M" value to megabytes; empty output on anything else.
to_mb() {
    local val="$1"
    if [[ "$val" =~ ^([0-9]+)([GgMm])$ ]]; then
        case "${BASH_REMATCH[2]}" in
            G | g) echo $((${BASH_REMATCH[1]} * 1024)) ;;
            M | m) echo "${BASH_REMATCH[1]}" ;;
        esac
    fi
}

# CONTAINER_MEMORY_LIMIT must exceed MEMORY_MAX (metaspace, thread stacks,
# direct buffers) or the container restart-loops; see .env.example. It must
# also fit in the host's actual RAM: the high-performance preset's 9G limit
# would get a container OOM-killed and restart-looping on a supported 4GB or
# 8GB Pi, so refuse (with an override) rather than apply it blind.
apply_memory() {
    local mem_min="$1" mem_max="$2" container_limit="$3"
    local total_ram_mb limit_mb
    total_ram_mb="$(free -m 2>/dev/null | awk '/^Mem:/{print $2}')"
    limit_mb="$(to_mb "$container_limit")"
    if [ -n "$total_ram_mb" ] && [ -n "$limit_mb" ] && [ "$limit_mb" -gt "$total_ram_mb" ]; then
        echo -e "${RED}CONTAINER_MEMORY_LIMIT=${container_limit} (~${limit_mb}MB) exceeds this host's ${total_ram_mb}MB of RAM.${NC}"
        echo -e "${YELLOW}Applying it anyway will likely get the container OOM-killed and restart-looping.${NC}"
        read -p "Apply anyway? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo -e "${YELLOW}Memory settings not changed.${NC}"
            return 1
        fi
    fi
    set_env_var MEMORY_MIN "$mem_min"
    set_env_var MEMORY_MAX "$mem_max"
    set_env_var CONTAINER_MEMORY_LIMIT "$container_limit"
    echo -e "${GREEN}Wrote MEMORY_MIN=${mem_min} MEMORY_MAX=${mem_max} CONTAINER_MEMORY_LIMIT=${container_limit} to ${ENV_FILE}${NC}"
}

# Function to apply low-end preset
apply_low_end() {
    echo -e "${BLUE}Applying Low-End Performance Preset (4GB Pi)...${NC}"
    echo ""

    # Server properties
    if [ -f "$SERVER_PROPERTIES" ]; then
        "$SCRIPT_DIR/server-properties-manager.sh" set view-distance 6 false
        "$SCRIPT_DIR/server-properties-manager.sh" set simulation-distance 4 false
        "$SCRIPT_DIR/server-properties-manager.sh" set max-players 5 false
        "$SCRIPT_DIR/server-properties-manager.sh" set network-compression-threshold 128 false
        "$SCRIPT_DIR/server-properties-manager.sh" set entity-broadcast-range-percentage 50 false
        "$SCRIPT_DIR/server-properties-manager.sh" set max-tick-time 60000 false
    fi

    apply_memory 1G 2G 3G || { echo -e "${YELLOW}Low-End preset stopped: memory not changed.${NC}"; return 1; }

    # JVM arguments
    echo -e "${BLUE}Generating JVM arguments...${NC}"
    "$SCRIPT_DIR/jvm-optimizer.sh" preset rpi 2G 4 > "${PROJECT_DIR}/.jvm-args" 2>&1 || true

    echo ""
    echo -e "${GREEN}✓ Low-End preset applied${NC}"
    echo -e "${YELLOW}Note: Restart server to apply changes${NC}"
}

# Function to apply balanced preset
apply_balanced() {
    echo -e "${BLUE}Applying Balanced Performance Preset (8GB Pi)...${NC}"
    echo ""

    # Server properties
    if [ -f "$SERVER_PROPERTIES" ]; then
        "$SCRIPT_DIR/server-properties-manager.sh" set view-distance 10 false
        "$SCRIPT_DIR/server-properties-manager.sh" set simulation-distance 8 false
        "$SCRIPT_DIR/server-properties-manager.sh" set max-players 10 false
        "$SCRIPT_DIR/server-properties-manager.sh" set network-compression-threshold 256 false
        "$SCRIPT_DIR/server-properties-manager.sh" set entity-broadcast-range-percentage 100 false
    fi

    apply_memory 2G 4G 5G || { echo -e "${YELLOW}Balanced preset stopped: memory not changed.${NC}"; return 1; }

    # JVM arguments
    echo -e "${BLUE}Generating JVM arguments...${NC}"
    "$SCRIPT_DIR/jvm-optimizer.sh" preset aikar 4G 4 > "${PROJECT_DIR}/.jvm-args" 2>&1 || true

    echo ""
    echo -e "${GREEN}✓ Balanced preset applied${NC}"
    echo -e "${YELLOW}Note: Restart server to apply changes${NC}"
}

# Function to apply high-performance preset
apply_high_performance() {
    echo -e "${BLUE}Applying High-Performance Preset...${NC}"
    echo ""

    # Server properties
    if [ -f "$SERVER_PROPERTIES" ]; then
        "$SCRIPT_DIR/server-properties-manager.sh" set view-distance 12 false
        "$SCRIPT_DIR/server-properties-manager.sh" set simulation-distance 10 false
        "$SCRIPT_DIR/server-properties-manager.sh" set max-players 20 false
        "$SCRIPT_DIR/server-properties-manager.sh" set network-compression-threshold 512 false
        "$SCRIPT_DIR/server-properties-manager.sh" set entity-broadcast-range-percentage 100 false
    fi

    apply_memory 4G 8G 9G || { echo -e "${YELLOW}High-Performance preset stopped: memory not changed.${NC}"; return 1; }

    # JVM arguments
    echo -e "${BLUE}Generating JVM arguments...${NC}"
    "$SCRIPT_DIR/jvm-optimizer.sh" preset aikar 8G 8 > "${PROJECT_DIR}/.jvm-args" 2>&1 || true

    echo ""
    echo -e "${GREEN}✓ High-Performance preset applied${NC}"
    echo -e "${YELLOW}Note: Restart server to apply changes${NC}"
}

# Function to show preset comparison
show_comparison() {
    echo -e "${BLUE}Performance Preset Comparison:${NC}"
    echo ""
    printf "%-20s %-15s %-15s %-15s\n" "Setting" "Low-End" "Balanced" "High-Perf"
    echo "─────────────────────────────────────────────────────────────"
    printf "%-20s %-15s %-15s %-15s\n" "View Distance" "6" "10" "12"
    printf "%-20s %-15s %-15s %-15s\n" "Simulation Distance" "4" "8" "10"
    printf "%-20s %-15s %-15s %-15s\n" "Max Players" "5" "10" "20"
    printf "%-20s %-15s %-15s %-15s\n" "Memory Min" "1G" "2G" "4G"
    printf "%-20s %-15s %-15s %-15s\n" "Memory Max" "2G" "4G" "8G"
    printf "%-20s %-15s %-15s %-15s\n" "Best For" "4GB Pi" "8GB Pi" "High-end"
    echo ""
}

# Function to show current settings
show_current() {
    echo -e "${BLUE}Current Server Settings:${NC}"
    echo ""

    if [ -f "$SERVER_PROPERTIES" ]; then
        echo "Server Properties:"
        "$SCRIPT_DIR/server-properties-manager.sh" get view-distance 2>/dev/null | sed 's/^/  View Distance: /' || echo "  View Distance: (not set)"
        "$SCRIPT_DIR/server-properties-manager.sh" get simulation-distance 2>/dev/null | sed 's/^/  Simulation Distance: /' || echo "  Simulation Distance: (not set)"
        "$SCRIPT_DIR/server-properties-manager.sh" get max-players 2>/dev/null | sed 's/^/  Max Players: /' || echo "  Max Players: (not set)"
    fi

    echo ""
    echo "Memory (.env, falling back to docker-compose.yml defaults):"
    show_env_or_default MEMORY_MIN 1G
    show_env_or_default MEMORY_MAX 2G
    show_env_or_default CONTAINER_MEMORY_LIMIT 3G

    echo ""
}

# Main function
main() {
    local command="${1:-help}"

    case "$command" in
        low-end|performance)
            apply_low_end
            ;;
        balanced)
            apply_balanced
            ;;
        high-performance|high)
            apply_high_performance
            ;;
        compare)
            show_comparison
            ;;
        current)
            show_current
            ;;
        help|*)
            echo -e "${BLUE}Performance Presets Manager${NC}"
            echo ""
            echo "Usage: $0 {preset|command} [options]"
            echo ""
            echo "Presets:"
            echo "  low-end          - Low-end performance (4GB Pi)"
            echo "  balanced         - Balanced performance (8GB Pi)"
            echo "  high-performance - High performance settings"
            echo ""
            echo "Commands:"
            echo "  compare          - Show preset comparison"
            echo "  current          - Show current settings"
            echo "  help             - Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0 low-end"
            echo "  $0 balanced"
            echo "  $0 compare"
            echo ""
            exit 1
            ;;
    esac
}

# Run main function
main "$@"
