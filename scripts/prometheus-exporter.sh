#!/bin/bash
# Prometheus Metrics Exporter for Minecraft Server
# Exposes metrics in Prometheus format on HTTP endpoint

set -e

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
METRICS_DIR="${PROJECT_DIR}/metrics"
EXPORTER_PORT=${PROMETHEUS_EXPORTER_PORT:-9091}

# Function to get metric value
get_metric() {
    local metric_name="$1"
    local default_value="${2:-0}"

    if [ -f "${METRICS_DIR}/${metric_name}.csv" ]; then
        # Get latest value from CSV
        tail -1 "${METRICS_DIR}/${metric_name}.csv" | cut -d',' -f4
    else
        echo "$default_value"
    fi
}

# Function to format Prometheus metric
format_metric() {
    local name="$1"
    local value="$2"
    local labels="${3:-}"

    if [ -n "$labels" ]; then
        echo "${name}{${labels}} ${value}"
    else
        echo "${name} ${value}"
    fi
}

# Function to generate metrics output
generate_metrics() {
    local timestamp=$(date +%s)

    echo "# HELP minecraft_server_up Server is running (1) or stopped (0)"
    echo "# TYPE minecraft_server_up gauge"

    if docker ps | grep -q minecraft-server; then
        echo "minecraft_server_up 1"
    else
        echo "minecraft_server_up 0"
        return
    fi

    echo ""
    echo "# HELP minecraft_server_cpu_usage_percent CPU usage percentage"
    echo "# TYPE minecraft_server_cpu_usage_percent gauge"

    local cpu=$(docker stats minecraft-server --no-stream --format "{{.CPUPerc}}" | sed 's/%//' 2>/dev/null || echo "0")
    echo "minecraft_server_cpu_usage_percent ${cpu}"

    echo ""
    echo "# HELP minecraft_server_memory_usage_bytes Memory usage in bytes"
    echo "# TYPE minecraft_server_memory_usage_bytes gauge"

    local mem_usage=$(docker stats minecraft-server --no-stream --format "{{.MemUsage}}" 2>/dev/null | cut -d'/' -f1 | sed 's/[^0-9]//g' || echo "0")
    # Convert to bytes (assuming MB input)
    local mem_bytes=$((mem_usage * 1024 * 1024))
    echo "minecraft_server_memory_usage_bytes ${mem_bytes}"

    echo ""
    echo "# HELP minecraft_server_memory_limit_bytes Memory limit in bytes"
    echo "# TYPE minecraft_server_memory_limit_bytes gauge"

    local mem_limit=$(docker stats minecraft-server --no-stream --format "{{.MemUsage}}" 2>/dev/null | cut -d'/' -f2 | sed 's/[^0-9]//g' || echo "0")
    local mem_limit_bytes=$((mem_limit * 1024 * 1024))
    echo "minecraft_server_memory_limit_bytes ${mem_limit_bytes}"

    echo ""
    echo "# HELP minecraft_server_player_count Current number of players"
    echo "# TYPE minecraft_server_player_count gauge"

    local players=$(docker logs minecraft-server --tail 100 2>/dev/null | grep -oP 'There are \K\d+' | tail -1 || echo "0")
    echo "minecraft_server_player_count ${players:-0}"

    echo ""
    echo "# HELP minecraft_server_uptime_seconds Server uptime in seconds"
    echo "# TYPE minecraft_server_uptime_seconds gauge"

    local started=$(docker inspect --format='{{.State.StartedAt}}' minecraft-server 2>/dev/null)
    if [ -n "$started" ]; then
        local start_epoch=$(date -d "$started" +%s 2>/dev/null || echo "0")
        local now_epoch=$(date +%s)
        local uptime=$((now_epoch - start_epoch))
        echo "minecraft_server_uptime_seconds ${uptime}"
    else
        echo "minecraft_server_uptime_seconds 0"
    fi

    echo ""
    echo "# HELP minecraft_server_tps Ticks per second"
    echo "# TYPE minecraft_server_tps gauge"

    local tps=$(get_metric "tps" "0")
    echo "minecraft_server_tps ${tps}"
}

# HTTP server function (simple implementation)
serve_metrics() {
    while true; do
        {
            echo "HTTP/1.1 200 OK"
            echo "Content-Type: text/plain; version=0.0.4"
            echo ""
            generate_metrics
        } | nc -l -p "$EXPORTER_PORT" 2>/dev/null || {
            # Fallback: just output metrics (can be used with a proper HTTP server)
            generate_metrics
            sleep 5
        }
    done
}

# Main function
main() {
    if [ "${1}" = "--serve" ]; then
        echo "Starting Prometheus exporter on port $EXPORTER_PORT"
        serve_metrics
    else
        # Just output metrics
        generate_metrics
    fi
}

main "$@"

