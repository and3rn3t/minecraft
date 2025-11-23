#!/bin/bash
# JVM Arguments Optimizer
# Generates optimized JVM arguments for Minecraft server

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

# Function to detect available memory
detect_memory() {
    # Try to get from docker-compose or environment
    local mem_max="${MEMORY_MAX:-2G}"

    # Extract number and unit
    if [[ "$mem_max" =~ ^([0-9]+)([GM])$ ]]; then
        local num="${BASH_REMATCH[1]}"
        local unit="${BASH_REMATCH[2]}"
        echo "${num}${unit}"
    else
        echo "2G"
    fi
}

# Function to detect CPU cores
detect_cores() {
    if command -v nproc >/dev/null 2>&1; then
        nproc
    elif [ -f /proc/cpuinfo ]; then
        grep -c processor /proc/cpuinfo
    else
        echo "4"
    fi
}

# Function to generate Aikar's Flags
generate_aikar_flags() {
    local memory="$1"
    local cores="$2"

    # Extract memory in GB
    local mem_gb
    if [[ "$memory" =~ ^([0-9]+)G$ ]]; then
        mem_gb="${BASH_REMATCH[1]}"
    elif [[ "$memory" =~ ^([0-9]+)M$ ]]; then
        mem_gb=$((BASH_REMATCH[1] / 1024))
        [ $mem_gb -eq 0 ] && mem_gb=1
    else
        mem_gb=2
    fi

    # Calculate heap sizes (Aikar's recommendations)
    local heap_min=$((mem_gb / 2))
    [ $heap_min -lt 1 ] && heap_min=1
    local heap_max=$((mem_gb - 1))
    [ $heap_max -lt 1 ] && heap_max=1

    # Generate flags
    local flags="-Xms${heap_min}G -Xmx${heap_max}G"
    flags+=" -XX:+UseG1GC"
    flags+=" -XX:+ParallelRefProcEnabled"
    flags+=" -XX:MaxGCPauseMillis=200"
    flags+=" -XX:+UnlockExperimentalVMOptions"
    flags+=" -XX:+DisableExplicitGC"
    flags+=" -XX:+AlwaysPreTouch"
    flags+=" -XX:G1NewSizePercent=30"
    flags+=" -XX:G1MaxNewSizePercent=40"
    flags+=" -XX:G1HeapRegionSize=8M"
    flags+=" -XX:G1ReservePercent=20"
    flags+=" -XX:G1HeapWastePercent=5"
    flags+=" -XX:G1MixedGCCountTarget=4"
    flags+=" -XX:InitiatingHeapOccupancyPercent=15"
    flags+=" -XX:G1MixedGCLiveThresholdPercent=90"
    flags+=" -XX:G1RSetUpdatingPauseTimePercent=5"
    flags+=" -XX:SurvivorRatio=32"
    flags+=" -XX:+PerfDisableSharedMem"
    flags+=" -XX:MaxTenuringThreshold=1"

    # Add thread-related flags
    flags+=" -Dusing.aikars.flags=https://mcflags.emc.gs"
    flags+=" -Daikars.new.flags=true"

    echo "$flags"
}

# Function to generate basic flags
generate_basic_flags() {
    local memory="$1"

    # Extract memory in GB
    local mem_gb
    if [[ "$memory" =~ ^([0-9]+)G$ ]]; then
        mem_gb="${BASH_REMATCH[1]}"
    elif [[ "$memory" =~ ^([0-9]+)M$ ]]; then
        mem_gb=$((BASH_REMATCH[1] / 1024))
        [ $mem_gb -eq 0 ] && mem_gb=1
    else
        mem_gb=2
    fi

    local heap_min=$((mem_gb / 2))
    [ $heap_min -lt 1 ] && heap_min=1
    local heap_max=$((mem_gb - 1))
    [ $heap_max -lt 1 ] && heap_max=1

    local flags="-Xms${heap_min}G -Xmx${heap_max}G"
    flags+=" -XX:+UseG1GC"
    flags+=" -XX:+UnlockExperimentalVMOptions"
    flags+=" -XX:+DisableExplicitGC"

    echo "$flags"
}

# Function to generate Raspberry Pi optimized flags
generate_rpi_flags() {
    local memory="$1"
    local cores="$2"

    # Extract memory in GB
    local mem_gb
    if [[ "$memory" =~ ^([0-9]+)G$ ]]; then
        mem_gb="${BASH_REMATCH[1]}"
    elif [[ "$memory" =~ ^([0-9]+)M$ ]]; then
        mem_gb=$((BASH_REMATCH[1] / 1024))
        [ $mem_gb -eq 0 ] && mem_gb=1
    else
        mem_gb=2
    fi

    local heap_min=$((mem_gb / 2))
    [ $heap_min -lt 1 ] && heap_min=1
    local heap_max=$((mem_gb - 1))
    [ $heap_max -lt 1 ] && heap_max=1

    local flags="-Xms${heap_min}G -Xmx${heap_max}G"
    flags+=" -XX:+UseG1GC"
    flags+=" -XX:MaxGCPauseMillis=200"
    flags+=" -XX:+UnlockExperimentalVMOptions"
    flags+=" -XX:+DisableExplicitGC"
    flags+=" -XX:+AlwaysPreTouch"
    flags+=" -XX:G1NewSizePercent=30"
    flags+=" -XX:G1MaxNewSizePercent=40"
    flags+=" -XX:G1HeapRegionSize=8M"
    flags+=" -XX:G1ReservePercent=20"
    flags+=" -XX:InitiatingHeapOccupancyPercent=15"
    flags+=" -XX:+PerfDisableSharedMem"
    flags+=" -XX:MaxTenuringThreshold=1"

    # Raspberry Pi specific optimizations
    flags+=" -XX:+UseStringDeduplication"
    flags+=" -Djava.awt.headless=true"

    echo "$flags"
}

# Function to apply preset
apply_preset() {
    local preset="$1"
    local memory="${2:-$(detect_memory)}"
    local cores="${3:-$(detect_cores)}"
    local server_type="${4:-vanilla}"

    case "$preset" in
        aikar|performance)
            generate_aikar_flags "$memory" "$cores"
            ;;
        basic|simple)
            generate_basic_flags "$memory"
            ;;
        rpi|raspberry-pi)
            generate_rpi_flags "$memory" "$cores"
            ;;
        *)
            echo -e "${RED}Error: Unknown preset: $preset${NC}"
            echo "Available presets: aikar, basic, rpi"
            return 1
            ;;
    esac
}

# Function to generate custom flags
generate_custom() {
    local memory="$1"
    local cores="$2"
    local server_type="$3"
    local preset="${4:-aikar}"

    apply_preset "$preset" "$memory" "$cores" "$server_type"
}

# Function to validate JVM arguments
validate_flags() {
    local flags="$1"

    # Basic validation
    if ! echo "$flags" | grep -qE "-Xms[0-9]+[GM]"; then
        echo -e "${RED}Error: Missing -Xms flag${NC}"
        return 1
    fi

    if ! echo "$flags" | grep -qE "-Xmx[0-9]+[GM]"; then
        echo -e "${RED}Error: Missing -Xmx flag${NC}"
        return 1
    fi

    return 0
}

# Function to save to file
save_flags() {
    local flags="$1"
    local output_file="${2:-${PROJECT_DIR}/.jvm-args}"

    echo "$flags" > "$output_file"
    echo -e "${GREEN}✓ JVM arguments saved to: $output_file${NC}"
}

# Main function
main() {
    local command="${1:-generate}"

    case "$command" in
        generate)
            local memory="${2:-$(detect_memory)}"
            local cores="${3:-$(detect_cores)}"
            local preset="${4:-aikar}"

            echo -e "${BLUE}Generating JVM arguments...${NC}"
            echo "  Memory: $memory"
            echo "  Cores: $cores"
            echo "  Preset: $preset"
            echo ""

            local flags=$(apply_preset "$preset" "$memory" "$cores")

            if validate_flags "$flags"; then
                echo -e "${GREEN}Generated JVM Arguments:${NC}"
                echo ""
                echo "$flags"
                echo ""
                echo -e "${YELLOW}To use these flags, add them to your server startup script${NC}"
            else
                echo -e "${RED}Error: Generated invalid JVM arguments${NC}"
                return 1
            fi
            ;;
        preset)
            if [ -z "$2" ]; then
                echo -e "${RED}Error: Preset name required${NC}"
                exit 1
            fi
            local memory="${3:-$(detect_memory)}"
            local cores="${4:-$(detect_cores)}"
            apply_preset "$2" "$memory" "$cores"
            ;;
        save)
            local memory="${2:-$(detect_memory)}"
            local cores="${3:-$(detect_cores)}"
            local preset="${4:-aikar}"
            local output_file="${5:-${PROJECT_DIR}/.jvm-args}"

            local flags=$(apply_preset "$preset" "$memory" "$cores")
            if validate_flags "$flags"; then
                save_flags "$flags" "$output_file"
            else
                echo -e "${RED}Error: Invalid flags${NC}"
                return 1
            fi
            ;;
        validate)
            if [ -z "$2" ]; then
                echo -e "${RED}Error: JVM arguments required${NC}"
                exit 1
            fi
            if validate_flags "$2"; then
                echo -e "${GREEN}✓ JVM arguments are valid${NC}"
            else
                echo -e "${RED}✗ JVM arguments are invalid${NC}"
                return 1
            fi
            ;;
        help|*)
            echo -e "${BLUE}JVM Arguments Optimizer${NC}"
            echo ""
            echo "Usage: $0 {command} [options]"
            echo ""
            echo "Commands:"
            echo "  generate [memory] [cores] [preset] - Generate optimized JVM arguments"
            echo "  preset <name> [memory] [cores]     - Apply preset"
            echo "  save [memory] [cores] [preset] [file] - Save to file"
            echo "  validate <flags>                  - Validate JVM arguments"
            echo "  help                              - Show this help message"
            echo ""
            echo "Presets:"
            echo "  aikar (default)  - Aikar's Flags (recommended)"
            echo "  basic            - Basic G1GC flags"
            echo "  rpi              - Raspberry Pi optimized"
            echo ""
            echo "Examples:"
            echo "  $0 generate"
            echo "  $0 generate 2G 4 aikar"
            echo "  $0 preset rpi 2G 4"
            echo "  $0 save 2G 4 aikar .jvm-args"
            echo ""
            exit 1
            ;;
    esac
}

# Run main function
main "$@"

