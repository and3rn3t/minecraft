#!/bin/bash
# Minecraft Server Monitoring Script
# Collects and logs server metrics

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
METRICS_DIR="${PROJECT_DIR}/metrics"
LOGS_DIR="${PROJECT_DIR}/logs"

# Create directories
mkdir -p "$METRICS_DIR" "$LOGS_DIR"

# Function to log metrics
log_metric() {
    local metric_name="$1"
    local value="$2"
    local timestamp=$(date +%s)
    local date_str=$(date +"%Y-%m-%d %H:%M:%S")

    # Append to metrics file (CSV format)
    echo "$timestamp,$date_str,$metric_name,$value" >> "${METRICS_DIR}/${metric_name}.csv"
}

# Function to get Docker container stats
get_container_stats() {
    if docker ps | grep -q minecraft-server; then
        docker stats minecraft-server --no-stream --format "{{.CPUPerc}},{{.MemUsage}},{{.MemPerc}},{{.NetIO}},{{.BlockIO}}"
    else
        echo "0%,0B / 0B,0%,0B / 0B,0B / 0B"
    fi
}

# Function to get memory usage
get_memory_usage() {
    if docker ps | grep -q minecraft-server; then
        local stats=$(docker stats minecraft-server --no-stream --format "{{.MemUsage}}")
        echo "$stats"
    else
        echo "0B / 0B"
    fi
}

# Function to get CPU usage
get_cpu_usage() {
    if docker ps | grep -q minecraft-server; then
        local cpu=$(docker stats minecraft-server --no-stream --format "{{.CPUPerc}}" | sed 's/%//')
        echo "$cpu"
    else
        echo "0"
    fi
}

# Function to get player count
get_player_count() {
    if docker ps | grep -q minecraft-server; then
        # Try to get player count from server logs or RCON
        local players=$(docker logs minecraft-server --tail 100 2>/dev/null | grep -oP 'There are \K\d+' | tail -1 || echo "0")
        echo "${players:-0}"
    else
        echo "0"
    fi
}

# Function to check server status
get_server_status() {
    if docker ps | grep -q minecraft-server; then
        # Check if container is healthy
        local health=$(docker inspect --format='{{.State.Health.Status}}' minecraft-server 2>/dev/null || echo "unknown")
        if [ "$health" = "healthy" ] || [ "$health" = "starting" ]; then
            echo "running"
        else
            echo "unhealthy"
        fi
    else
        echo "stopped"
    fi
}

# Function to get server uptime
get_server_uptime() {
    if docker ps | grep -q minecraft-server; then
        local started=$(docker inspect --format='{{.State.StartedAt}}' minecraft-server 2>/dev/null)
        if [ -n "$started" ]; then
            local start_epoch=$(date -d "$started" +%s 2>/dev/null || echo "0")
            local now_epoch=$(date +%s)
            local uptime=$((now_epoch - start_epoch))
            echo "$uptime"
        else
            echo "0"
        fi
    else
        echo "0"
    fi
}

# Function to get TPS (Ticks Per Second) from logs
get_tps() {
    if docker ps | grep -q minecraft-server; then
        # Try to extract TPS from recent logs
        # Minecraft servers often log TPS in format like "TPS: 20.0"
        local tps=$(docker logs minecraft-server --tail 500 2>/dev/null | \
            grep -iE '(tps|ticks per second)' | \
            tail -1 | \
            grep -oE '[0-9]+\.[0-9]+' | \
            head -1 || echo "0")
        echo "${tps:-0}"
    else
        echo "0"
    fi
}

# Main monitoring function
main() {
    local timestamp=$(date +"%Y-%m-%d %H:%M:%S")
    echo "[$timestamp] Collecting metrics..."

    # Collect metrics
    local status=$(get_server_status)
    local cpu=$(get_cpu_usage)
    local memory=$(get_memory_usage)
    local players=$(get_player_count)
    local uptime=$(get_server_uptime)
    local tps=$(get_tps)

    # Log metrics
    log_metric "server_status" "$status"
    log_metric "cpu_usage" "$cpu"
    log_metric "memory_usage" "$memory"
    log_metric "player_count" "$players"
    log_metric "server_uptime" "$uptime"
    log_metric "tps" "$tps"

    # Log to combined metrics file
    echo "$(date +%s),$(date +"%Y-%m-%d %H:%M:%S"),status,$status,cpu,$cpu,memory,$memory,players,$players,uptime,$uptime,tps,$tps" >> "${METRICS_DIR}/all_metrics.csv"

    echo "[$timestamp] Metrics collected: status=$status, cpu=${cpu}%, players=$players, tps=$tps"
}

# Run main function
main "$@"

