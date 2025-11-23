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
DOCKER_COMPOSE="${DOCKER_COMPOSE:-${PROJECT_DIR}/docker-compose.yml}"

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

    # Docker compose memory
    if [ -f "$DOCKER_COMPOSE" ]; then
        echo -e "${YELLOW}Note: Update docker-compose.yml manually:${NC}"
        echo "  MEMORY_MIN=1G"
        echo "  MEMORY_MAX=2G"
    fi

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

    # Docker compose memory
    if [ -f "$DOCKER_COMPOSE" ]; then
        echo -e "${YELLOW}Note: Update docker-compose.yml manually:${NC}"
        echo "  MEMORY_MIN=2G"
        echo "  MEMORY_MAX=4G"
    fi

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

    # Docker compose memory
    if [ -f "$DOCKER_COMPOSE" ]; then
        echo -e "${YELLOW}Note: Update docker-compose.yml manually:${NC}"
        echo "  MEMORY_MIN=4G"
        echo "  MEMORY_MAX=8G"
    fi

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

    if [ -f "$DOCKER_COMPOSE" ]; then
        echo ""
        echo "Docker Compose:"
        grep "MEMORY_MIN" "$DOCKER_COMPOSE" 2>/dev/null | sed 's/^/  /' || echo "  MEMORY_MIN: (not set)"
        grep "MEMORY_MAX" "$DOCKER_COMPOSE" 2>/dev/null | sed 's/^/  /' || echo "  MEMORY_MAX: (not set)"
    fi

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

