#!/bin/bash
# Minecraft Server Performance Benchmark Suite
# Measures server performance and creates baselines for regression testing

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
BENCHMARK_DIR="${PROJECT_DIR}/benchmarks"
RESULTS_DIR="${BENCHMARK_DIR}/results"
BASELINE_DIR="${BENCHMARK_DIR}/baselines"

# Create directories
mkdir -p "$BENCHMARK_DIR" "$RESULTS_DIR" "$BASELINE_DIR"

# Benchmark configuration
WARMUP_TIME=${WARMUP_TIME:-60}          # Warmup time in seconds
BENCHMARK_DURATION=${BENCHMARK_DURATION:-300}  # Benchmark duration in seconds
SAMPLING_INTERVAL=${SAMPLING_INTERVAL:-5}     # Sampling interval in seconds

# Results storage
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
RESULT_FILE="${RESULTS_DIR}/benchmark_${TIMESTAMP}.json"
BASELINE_FILE="${BASELINE_DIR}/baseline.json"

# Function to print header
print_header() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
}

# Function to check if server is running
check_server_running() {
    if ! docker ps | grep -q minecraft-server; then
        echo -e "${RED}Error: Minecraft server is not running${NC}"
        echo "Start the server with: ./manage.sh start"
        exit 1
    fi
}

# Function to wait for server to be ready
wait_for_server_ready() {
    local max_wait=${1:-120}
    local waited=0

    echo -e "${YELLOW}Waiting for server to be ready...${NC}"

    while [ $waited -lt $max_wait ]; do
        if docker logs minecraft-server --tail 50 2>/dev/null | grep -q "Done"; then
            echo -e "${GREEN}Server is ready!${NC}"
            return 0
        fi
        sleep 2
        waited=$((waited + 2))
        echo -n "."
    done

    echo -e "${RED}Server did not become ready within ${max_wait} seconds${NC}"
    return 1
}

# Function to measure startup time
benchmark_startup_time() {
    print_header "Benchmark: Server Startup Time"

    local start_time=$(date +%s.%N)

    echo -e "${BLUE}Stopping server...${NC}"
    docker-compose stop minecraft >/dev/null 2>&1 || true
    sleep 5

    echo -e "${BLUE}Starting server...${NC}"
    docker-compose up -d minecraft

    wait_for_server_ready 180

    local end_time=$(date +%s.%N)
    local startup_time=$(echo "$end_time - $start_time" | bc)

    echo -e "${GREEN}Startup time: ${startup_time}s${NC}"
    echo ""

    echo "{\"startup_time\": $startup_time}" > "${RESULTS_DIR}/startup_${TIMESTAMP}.json"
    echo "$startup_time"
}

# Function to measure TPS (Ticks Per Second)
benchmark_tps() {
    print_header "Benchmark: TPS (Ticks Per Second)"

    local samples=()
    local sample_count=$((BENCHMARK_DURATION / SAMPLING_INTERVAL))

    echo -e "${BLUE}Collecting TPS samples for ${BENCHMARK_DURATION} seconds...${NC}"
    echo -e "${BLUE}Sampling every ${SAMPLING_INTERVAL} seconds (${sample_count} samples)${NC}"
    echo ""

    for ((i=0; i<sample_count; i++)); do
        # Try to get TPS from logs (Paper/Spigot)
        local tps=$(docker logs minecraft-server --tail 200 2>/dev/null | \
            grep -oP 'TPS from last 1m, 5m, 15m: \K[\d.]+' | tail -1 || echo "20.0")

        # If not found, try alternative patterns
        if [ "$tps" = "20.0" ]; then
            tps=$(docker logs minecraft-server --tail 200 2>/dev/null | \
                grep -oP 'tps: \K[\d.]+' | tail -1 || echo "20.0")
        fi

        samples+=("$tps")
        echo -e "Sample $((i+1))/$sample_count: TPS = ${tps}"
        sleep "$SAMPLING_INTERVAL"
    done

    # Calculate statistics
    local sum=0
    local min=20.0
    local max=0.0

    for tps in "${samples[@]}"; do
        sum=$(echo "$sum + $tps" | bc)
        if (( $(echo "$tps < $min" | bc -l) )); then
            min=$tps
        fi
        if (( $(echo "$tps > $max" | bc -l) )); then
            max=$tps
        fi
    done

    local avg=$(echo "scale=2; $sum / ${#samples[@]}" | bc)

    echo ""
    echo -e "${GREEN}TPS Statistics:${NC}"
    echo -e "  Average: ${avg}"
    echo -e "  Minimum: ${min}"
    echo -e "  Maximum: ${max}"
    echo ""

    echo "{\"tps_avg\": $avg, \"tps_min\": $min, \"tps_max\": $max, \"samples\": [$(IFS=,; echo "${samples[*]}")]}" > "${RESULTS_DIR}/tps_${TIMESTAMP}.json"
    echo "$avg"
}

# Function to measure memory usage
benchmark_memory() {
    print_header "Benchmark: Memory Usage"

    local samples=()
    local sample_count=$((BENCHMARK_DURATION / SAMPLING_INTERVAL))

    echo -e "${BLUE}Collecting memory samples for ${BENCHMARK_DURATION} seconds...${NC}"
    echo ""

    for ((i=0; i<sample_count; i++)); do
        local mem_usage=$(docker stats minecraft-server --no-stream --format "{{.MemUsage}}" 2>/dev/null | \
            awk '{print $1}' | sed 's/[^0-9.]//g' || echo "0")

        # Convert to MB if needed
        local mem_mb=$(echo "$mem_usage" | awk '{if ($1 ~ /[0-9]+Gi/) print $1*1024; else if ($1 ~ /[0-9]+Mi/) print $1; else print $1/1024/1024}')

        samples+=("$mem_mb")
        echo -e "Sample $((i+1))/$sample_count: Memory = ${mem_mb}MB"
        sleep "$SAMPLING_INTERVAL"
    done

    # Calculate statistics
    local sum=0
    local min=999999
    local max=0

    for mem in "${samples[@]}"; do
        sum=$(echo "$sum + $mem" | bc)
        if (( $(echo "$mem < $min" | bc -l) )); then
            min=$mem
        fi
        if (( $(echo "$mem > $max" | bc -l) )); then
            max=$mem
        fi
    done

    local avg=$(echo "scale=2; $sum / ${#samples[@]}" | bc)

    echo ""
    echo -e "${GREEN}Memory Statistics:${NC}"
    echo -e "  Average: ${avg}MB"
    echo -e "  Minimum: ${min}MB"
    echo -e "  Maximum: ${max}MB"
    echo ""

    echo "{\"memory_avg\": $avg, \"memory_min\": $min, \"memory_max\": $max, \"samples\": [$(IFS=,; echo "${samples[*]}")]}" > "${RESULTS_DIR}/memory_${TIMESTAMP}.json"
    echo "$avg"
}

# Function to measure CPU usage
benchmark_cpu() {
    print_header "Benchmark: CPU Usage"

    local samples=()
    local sample_count=$((BENCHMARK_DURATION / SAMPLING_INTERVAL))

    echo -e "${BLUE}Collecting CPU samples for ${BENCHMARK_DURATION} seconds...${NC}"
    echo ""

    for ((i=0; i<sample_count; i++)); do
        local cpu=$(docker stats minecraft-server --no-stream --format "{{.CPUPerc}}" 2>/dev/null | \
            sed 's/%//' || echo "0")

        samples+=("$cpu")
        echo -e "Sample $((i+1))/$sample_count: CPU = ${cpu}%"
        sleep "$SAMPLING_INTERVAL"
    done

    # Calculate statistics
    local sum=0
    local min=100
    local max=0

    for cpu in "${samples[@]}"; do
        sum=$(echo "$sum + $cpu" | bc)
        if (( $(echo "$cpu < $min" | bc -l) )); then
            min=$cpu
        fi
        if (( $(echo "$cpu > $max" | bc -l) )); then
            max=$cpu
        fi
    done

    local avg=$(echo "scale=2; $sum / ${#samples[@]}" | bc)

    echo ""
    echo -e "${GREEN}CPU Statistics:${NC}"
    echo -e "  Average: ${avg}%"
    echo -e "  Minimum: ${min}%"
    echo -e "  Maximum: ${max}%"
    echo ""

    echo "{\"cpu_avg\": $avg, \"cpu_min\": $min, \"cpu_max\": $max, \"samples\": [$(IFS=,; echo "${samples[*]}")]}" > "${RESULTS_DIR}/cpu_${TIMESTAMP}.json"
    echo "$avg"
}

# Function to create baseline
create_baseline() {
    print_header "Creating Performance Baseline"

    check_server_running

    echo -e "${BLUE}Running full benchmark suite...${NC}"
    echo ""

    # Warmup period
    echo -e "${YELLOW}Warmup period: ${WARMUP_TIME} seconds${NC}"
    sleep "$WARMUP_TIME"
    echo ""

    # Run benchmarks
    local startup_time=$(benchmark_startup_time)
    sleep 10  # Let server stabilize

    wait_for_server_ready
    sleep "$WARMUP_TIME"  # Warmup after restart

    local tps_avg=$(benchmark_tps)
    local memory_avg=$(benchmark_memory)
    local cpu_avg=$(benchmark_cpu)

    # Create baseline JSON
    cat > "$BASELINE_FILE" <<EOF
{
  "timestamp": "$(date -Iseconds)",
  "version": "$(docker exec minecraft-server java -version 2>&1 | head -1 || echo 'unknown')",
  "minecraft_version": "${MINECRAFT_VERSION:-1.20.4}",
  "server_type": "${SERVER_TYPE:-vanilla}",
  "memory_min": "${MEMORY_MIN:-1G}",
  "memory_max": "${MEMORY_MAX:-2G}",
  "metrics": {
    "startup_time": $startup_time,
    "tps_avg": $tps_avg,
    "memory_avg": $memory_avg,
    "cpu_avg": $cpu_avg
  },
  "thresholds": {
    "startup_time_max": $(echo "$startup_time * 1.2" | bc),
    "tps_min": 18.0,
    "memory_max": $(echo "$memory_avg * 1.3" | bc),
    "cpu_max": $(echo "$cpu_avg * 1.5" | bc)
  }
}
EOF

    echo -e "${GREEN}Baseline created: $BASELINE_FILE${NC}"
    echo ""
    cat "$BASELINE_FILE" | python3 -m json.tool 2>/dev/null || cat "$BASELINE_FILE"
    echo ""
}

# Function to compare against baseline
compare_baseline() {
    print_header "Comparing Against Baseline"

    if [ ! -f "$BASELINE_FILE" ]; then
        echo -e "${RED}No baseline found. Create one first with: $0 baseline${NC}"
        exit 1
    fi

    check_server_running

    # Run quick benchmark
    wait_for_server_ready
    sleep "$WARMUP_TIME"

    local tps_avg=$(benchmark_tps)
    local memory_avg=$(benchmark_memory)
    local cpu_avg=$(benchmark_cpu)

    # Load baseline
    local baseline_tps=$(python3 -c "import json; print(json.load(open('$BASELINE_FILE'))['metrics']['tps_avg'])" 2>/dev/null || echo "20.0")
    local baseline_memory=$(python3 -c "import json; print(json.load(open('$BASELINE_FILE'))['metrics']['memory_avg'])" 2>/dev/null || echo "0")
    local baseline_cpu=$(python3 -c "import json; print(json.load(open('$BASELINE_FILE'))['metrics']['cpu_avg'])" 2>/dev/null || echo "0")

    # Compare
    echo -e "${BLUE}Comparison Results:${NC}"
    echo ""

    # TPS comparison
    local tps_diff=$(echo "$tps_avg - $baseline_tps" | bc)
    local tps_pct=$(echo "scale=1; ($tps_diff / $baseline_tps) * 100" | bc)
    if (( $(echo "$tps_avg < 18.0" | bc -l) )); then
        echo -e "${RED}TPS: ${tps_avg} (baseline: ${baseline_tps}) - ${tps_pct}% change - ⚠️  BELOW THRESHOLD${NC}"
    elif (( $(echo "$tps_diff < 0" | bc -l) )); then
        echo -e "${YELLOW}TPS: ${tps_avg} (baseline: ${baseline_tps}) - ${tps_pct}% change - ⚠️  REGRESSION${NC}"
    else
        echo -e "${GREEN}TPS: ${tps_avg} (baseline: ${baseline_tps}) - +${tps_pct}% change - ✓ OK${NC}"
    fi

    # Memory comparison
    local mem_diff=$(echo "$memory_avg - $baseline_memory" | bc)
    local mem_pct=$(echo "scale=1; ($mem_diff / $baseline_memory) * 100" | bc)
    if (( $(echo "$mem_diff > 0" | bc -l) )); then
        echo -e "${YELLOW}Memory: ${memory_avg}MB (baseline: ${baseline_memory}MB) - +${mem_pct}% change - ⚠️  INCREASE${NC}"
    else
        echo -e "${GREEN}Memory: ${memory_avg}MB (baseline: ${baseline_memory}MB) - ${mem_pct}% change - ✓ OK${NC}"
    fi

    # CPU comparison
    local cpu_diff=$(echo "$cpu_avg - $baseline_cpu" | bc)
    local cpu_pct=$(echo "scale=1; ($cpu_diff / $baseline_cpu) * 100" | bc)
    if (( $(echo "$cpu_avg > 80" | bc -l) )); then
        echo -e "${RED}CPU: ${cpu_avg}% (baseline: ${baseline_cpu}%) - ${cpu_pct}% change - ⚠️  HIGH USAGE${NC}"
    elif (( $(echo "$cpu_diff > 0" | bc -l) )); then
        echo -e "${YELLOW}CPU: ${cpu_avg}% (baseline: ${baseline_cpu}%) - +${cpu_pct}% change - ⚠️  INCREASE${NC}"
    else
        echo -e "${GREEN}CPU: ${cpu_avg}% (baseline: ${baseline_cpu}%) - ${cpu_pct}% change - ✓ OK${NC}"
    fi

    echo ""
}

# Function to run all benchmarks
run_all() {
    print_header "Running Full Benchmark Suite"

    check_server_running

    create_baseline
    compare_baseline
}

# Main function
main() {
    local command="${1:-help}"

    case "$command" in
        startup)
            check_server_running
            benchmark_startup_time
            ;;
        tps)
            check_server_running
            wait_for_server_ready
            benchmark_tps
            ;;
        memory)
            check_server_running
            benchmark_memory
            ;;
        cpu)
            check_server_running
            benchmark_cpu
            ;;
        baseline)
            create_baseline
            ;;
        compare)
            compare_baseline
            ;;
        all)
            run_all
            ;;
        help|*)
            echo -e "${BLUE}Minecraft Server Performance Benchmark Suite${NC}"
            echo ""
            echo "Usage: $0 {startup|tps|memory|cpu|baseline|compare|all}"
            echo ""
            echo "Commands:"
            echo "  startup   - Benchmark server startup time"
            echo "  tps       - Benchmark TPS (Ticks Per Second)"
            echo "  memory    - Benchmark memory usage"
            echo "  cpu       - Benchmark CPU usage"
            echo "  baseline  - Create performance baseline"
            echo "  compare   - Compare current performance against baseline"
            echo "  all       - Run full benchmark suite (baseline + compare)"
            echo ""
            echo "Environment Variables:"
            echo "  WARMUP_TIME=${WARMUP_TIME} - Warmup time in seconds"
            echo "  BENCHMARK_DURATION=${BENCHMARK_DURATION} - Benchmark duration in seconds"
            echo "  SAMPLING_INTERVAL=${SAMPLING_INTERVAL} - Sampling interval in seconds"
            echo ""
            exit 1
            ;;
    esac
}

# Check for bc (required for calculations)
if ! command -v bc >/dev/null 2>&1; then
    echo -e "${RED}Error: 'bc' command not found. Install with: sudo apt-get install bc${NC}"
    exit 1
fi

# Run main function
main "$@"

