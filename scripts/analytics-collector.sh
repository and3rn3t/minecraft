#!/bin/bash
# Advanced Analytics Data Collector
# Collects detailed metrics for analytics and behavior analysis

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
ANALYTICS_DIR="${PROJECT_DIR}/analytics"
METRICS_DIR="${PROJECT_DIR}/metrics"
LOGS_DIR="${PROJECT_DIR}/logs"

# Create directories
mkdir -p "$ANALYTICS_DIR" "$METRICS_DIR" "$LOGS_DIR"

# Function to log analytics data in JSON format
log_analytics() {
    local data_type="$1"
    local data="$2"
    local timestamp=$(date +%s)
    local date_str=$(date +"%Y-%m-%d %H:%M:%S")
    local file="${ANALYTICS_DIR}/${data_type}.jsonl"

    # Append JSON line to file
    echo "{\"timestamp\":$timestamp,\"datetime\":\"$date_str\",\"data\":$data}" >> "$file"
}

# Function to get detailed player information
get_player_analytics() {
    if ! docker ps | grep -q minecraft-server; then
        echo "[]"
        return
    fi

    # Try to get player list via RCON or logs
    local players_json="[]"

    # Check if RCON is available
    if [ -f "${PROJECT_DIR}/config/rcon.conf" ]; then
        local rcon_password=$(grep "^password=" "${PROJECT_DIR}/config/rcon.conf" | cut -d= -f2)
        if [ -n "$rcon_password" ]; then
            # Get player list via RCON
            local list_output=$(docker exec minecraft-server rcon-cli list 2>/dev/null || echo "")
            if [ -n "$list_output" ]; then
                # Parse player list (format: "There are X of a max of Y players online: player1, player2")
                local player_count=$(echo "$list_output" | grep -oP 'There are \K\d+' || echo "0")
                local players=$(echo "$list_output" | grep -oP 'online: \K.*' || echo "")

                if [ -n "$players" ] && [ "$players" != " " ]; then
                    # Convert comma-separated list to JSON array
                    players_json=$(echo "$players" | sed "s/, /\",\"/g" | sed "s/^/\"/" | sed "s/$/\"/" | sed "s/^/[/" | sed "s/$/]/")
                else
                    players_json="[]"
                fi
            fi
        fi
    fi

    echo "$players_json"
}

# Function to get player join/leave events from logs
get_player_events() {
    if ! docker ps | grep -q minecraft-server; then
        echo "[]"
        return
    fi

    local events="[]"
    local log_file="${LOGS_DIR}/latest.log"

    # Get recent log entries (last 100 lines)
    if [ -f "$log_file" ]; then
        local recent_logs=$(tail -100 "$log_file" 2>/dev/null || echo "")
    else
        # Try to get from Docker logs
        recent_logs=$(docker logs minecraft-server --tail 100 2>/dev/null || echo "")
    fi

    # Parse join/leave events
    local join_events=$(echo "$recent_logs" | grep -i "joined the game" | tail -10 || echo "")
    local leave_events=$(echo "$recent_logs" | grep -iE "(left the game|disconnected)" | tail -10 || echo "")

    # Build events array (simplified - would need more parsing in production)
    if [ -n "$join_events" ] || [ -n "$leave_events" ]; then
        events="[{\"type\":\"join\",\"count\":$(echo "$join_events" | wc -l)},{\"type\":\"leave\",\"count\":$(echo "$leave_events" | wc -l)}]"
    fi

    echo "$events"
}

# Function to get server performance metrics
get_performance_metrics() {
    if ! docker ps | grep -q minecraft-server; then
        echo "{\"tps\":0,\"cpu\":0,\"memory\":0,\"chunks_loaded\":0}"
        return
    fi

    local tps=0
    local cpu=0
    local memory=0
    local chunks_loaded=0

    # Get TPS from logs
    if docker logs minecraft-server --tail 500 2>/dev/null | grep -qiE "(tps|ticks per second)"; then
        tps=$(docker logs minecraft-server --tail 500 2>/dev/null | \
            grep -iE '(tps|ticks per second)' | \
            tail -1 | \
            grep -oE '[0-9]+\.[0-9]+' | \
            head -1 || echo "0")
    fi

    # Get CPU usage
    if docker stats minecraft-server --no-stream --format "{{.CPUPerc}}" 2>/dev/null | grep -q "%"; then
        cpu=$(docker stats minecraft-server --no-stream --format "{{.CPUPerc}}" 2>/dev/null | sed 's/%//' || echo "0")
    fi

    # Get memory usage (in MB)
    local mem_stats=$(docker stats minecraft-server --no-stream --format "{{.MemUsage}}" 2>/dev/null || echo "0B / 0B")
    if echo "$mem_stats" | grep -q "MiB"; then
        memory=$(echo "$mem_stats" | grep -oP '\d+\.\d+MiB' | head -1 | sed 's/MiB//' || echo "0")
    elif echo "$mem_stats" | grep -q "GiB"; then
        local mem_gb=$(echo "$mem_stats" | grep -oP '\d+\.\d+GiB' | head -1 | sed 's/GiB//' || echo "0")
        memory=$(echo "$mem_gb * 1024" | bc 2>/dev/null || echo "0")
    fi

    # Try to get chunks loaded (from logs or RCON)
    if [ -f "${PROJECT_DIR}/config/rcon.conf" ]; then
        local rcon_password=$(grep "^password=" "${PROJECT_DIR}/config/rcon.conf" | cut -d= -f2)
        if [ -n "$rcon_password" ]; then
            # Try to get chunk info (this would need server-specific commands)
            chunks_loaded=0  # Placeholder - would need mod/plugin support
        fi
    fi

    echo "{\"tps\":$tps,\"cpu\":$cpu,\"memory\":$memory,\"chunks_loaded\":$chunks_loaded}"
}

# Function to get network metrics
get_network_metrics() {
    if ! docker ps | grep -q minecraft-server; then
        echo "{\"bytes_sent\":0,\"bytes_recv\":0,\"packets_sent\":0,\"packets_recv\":0}"
        return
    fi

    local net_io=$(docker stats minecraft-server --no-stream --format "{{.NetIO}}" 2>/dev/null || echo "0B / 0B")
    local bytes_sent=0
    local bytes_recv=0

    # Parse network I/O (format: "1.2GB / 500MB")
    if echo "$net_io" | grep -q " / "; then
        bytes_recv=$(echo "$net_io" | cut -d'/' -f1 | sed 's/[^0-9.]//g' || echo "0")
        bytes_sent=$(echo "$net_io" | cut -d'/' -f2 | sed 's/[^0-9.]//g' || echo "0")
    fi

    echo "{\"bytes_sent\":$bytes_sent,\"bytes_recv\":$bytes_recv,\"packets_sent\":0,\"packets_recv\":0}"
}

# Function to get world statistics
get_world_stats() {
    if ! docker ps | grep -q minecraft-server; then
        echo "{\"world_size_mb\":0,\"region_count\":0,\"entities\":0}"
        return
    fi

    local world_size=0
    local region_count=0
    local entities=0

    # Get world directory size
    if [ -d "${PROJECT_DIR}/data/world" ]; then
        world_size=$(du -sm "${PROJECT_DIR}/data/world" 2>/dev/null | cut -f1 || echo "0")
        region_count=$(find "${PROJECT_DIR}/data/world/region" -name "*.mca" 2>/dev/null | wc -l || echo "0")
    fi

    # Try to get entity count via RCON
    if [ -f "${PROJECT_DIR}/config/rcon.conf" ]; then
        local rcon_password=$(grep "^password=" "${PROJECT_DIR}/config/rcon.conf" | cut -d= -f2)
        if [ -n "$rcon_password" ]; then
            # Entity count would need server command support
            entities=0  # Placeholder
        fi
    fi

    echo "{\"world_size_mb\":$world_size,\"region_count\":$region_count,\"entities\":$entities}"
}

# Main collection function
main() {
    local timestamp=$(date +"%Y-%m-%d %H:%M:%S")
    echo -e "${BLUE}[$timestamp]${NC} Collecting analytics data..."

    # Collect player analytics
    local players=$(get_player_analytics)
    log_analytics "players" "$players"

    # Collect player events
    local events=$(get_player_events)
    log_analytics "player_events" "$events"

    # Collect performance metrics
    local performance=$(get_performance_metrics)
    log_analytics "performance" "$performance"

    # Collect network metrics
    local network=$(get_network_metrics)
    log_analytics "network" "$network"

    # Collect world statistics
    local world_stats=$(get_world_stats)
    log_analytics "world_stats" "$world_stats"

    # Collect system metrics (CPU temp, etc. for RPi)
    if command -v vcgencmd &> /dev/null; then
        local temp=$(vcgencmd measure_temp | cut -d= -f2 | cut -d\' -f1 || echo "0")
        local freq=$(vcgencmd measure_clock arm | awk -F= '{print $2/1000000}' || echo "0")
        local throttled=$(vcgencmd get_throttled | cut -d= -f2 || echo "0x0")
        local system_metrics="{\"cpu_temp\":$temp,\"cpu_freq_mhz\":$freq,\"throttled\":\"$throttled\"}"
        log_analytics "system" "$system_metrics"
    fi

    echo -e "${GREEN}[$timestamp]${NC} Analytics data collected successfully"
}

# Run main function
main "$@"

