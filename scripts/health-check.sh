#!/bin/bash
# Health Check Script for Minecraft Server
# Returns exit code 0 if healthy, non-zero if unhealthy
# Can be used by Docker healthcheck or monitoring systems

set -e

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Health check thresholds
MAX_CPU_PERCENT=90
MAX_MEMORY_PERCENT=95
MIN_TPS=15.0
MAX_RESPONSE_TIME=5

# Function to check if server container is running
check_container_running() {
    if ! docker ps | grep -q minecraft-server; then
        echo "ERROR: Server container is not running"
        return 1
    fi
    return 0
}

# Function to check CPU usage
check_cpu() {
    if docker ps | grep -q minecraft-server; then
        local cpu=$(docker stats minecraft-server --no-stream --format "{{.CPUPerc}}" | sed 's/%//')
        local cpu_int=${cpu%.*}

        if [ "$cpu_int" -gt "$MAX_CPU_PERCENT" ]; then
            echo "WARNING: CPU usage is ${cpu}% (threshold: ${MAX_CPU_PERCENT}%)"
            return 1
        fi
    fi
    return 0
}

# Function to check memory usage
check_memory() {
    if docker ps | grep -q minecraft-server; then
        local mem_perc=$(docker stats minecraft-server --no-stream --format "{{.MemPerc}}" | sed 's/%//')
        local mem_int=${mem_perc%.*}

        if [ "$mem_int" -gt "$MAX_MEMORY_PERCENT" ]; then
            echo "WARNING: Memory usage is ${mem_perc}% (threshold: ${MAX_MEMORY_PERCENT}%)"
            return 1
        fi
    fi
    return 0
}

# Function to check if Java process is running
check_java_process() {
    if docker ps | grep -q minecraft-server; then
        if docker exec minecraft-server pgrep -f java > /dev/null 2>&1; then
            return 0
        else
            echo "ERROR: Java process not found in container"
            return 1
        fi
    fi
    return 1
}

# Function to check server port
check_port() {
    local port=${SERVER_PORT:-25565}
    if netstat -tuln 2>/dev/null | grep -q ":$port " || \
       ss -tuln 2>/dev/null | grep -q ":$port "; then
        return 0
    else
        echo "WARNING: Server port $port is not listening"
        return 1
    fi
}

# Function to check TPS (if available)
check_tps() {
    # This is a basic check - TPS monitoring would need RCON or log parsing
    # For now, we'll just check if we can get any response
    return 0
}

# Main health check
main() {
    local exit_code=0

    # Run all checks
    if ! check_container_running; then
        exit_code=1
    fi

    if ! check_java_process; then
        exit_code=1
    fi

    if ! check_port; then
        exit_code=1
    fi

    # These are warnings, not critical failures
    if ! check_cpu; then
        exit_code=1
    fi

    if ! check_memory; then
        exit_code=1
    fi

    if [ $exit_code -eq 0 ]; then
        echo "OK: Server is healthy"
    fi

    return $exit_code
}

# Run main function
main "$@"

