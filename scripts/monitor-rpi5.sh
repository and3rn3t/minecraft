#!/bin/bash
# Enhanced Raspberry Pi 5 Performance Monitor
# Provides comprehensive system and Minecraft server monitoring

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Check if running on Raspberry Pi
if [ ! -f /proc/device-tree/model ]; then
    echo -e "${YELLOW}Warning: This script is designed for Raspberry Pi${NC}"
fi

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Raspberry Pi 5 Performance Monitor${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# System Information
echo -e "${CYAN}=== System Information ===${NC}"
if [ -f /proc/device-tree/model ]; then
    MODEL=$(cat /proc/device-tree/model)
    echo -e "Model: ${GREEN}${MODEL}${NC}"
fi

ARCH=$(uname -m)
echo -e "Architecture: ${GREEN}${ARCH}${NC}"

UPTIME=$(uptime -p)
echo -e "Uptime: ${GREEN}${UPTIME}${NC}"
echo ""

# CPU Information
echo -e "${CYAN}=== CPU Information ===${NC}"
if command -v vcgencmd &> /dev/null; then
    CPU_TEMP=$(vcgencmd measure_temp | cut -d= -f2)
    echo -e "Temperature: ${GREEN}${CPU_TEMP}${NC}"

    CPU_FREQ=$(vcgencmd measure_clock arm | awk -F= '{printf "%.0f MHz", $2/1000000}')
    echo -e "Frequency: ${GREEN}${CPU_FREQ}${NC}"

    THROTTLED=$(vcgencmd get_throttled | cut -d= -f2)
    if [ "$THROTTLED" = "0x0" ]; then
        echo -e "Throttling: ${GREEN}None${NC}"
    else
        echo -e "Throttling: ${RED}Detected (${THROTTLED})${NC}"
    fi

    VOLTAGE=$(vcgencmd measure_volts | cut -d= -f2)
    echo -e "Voltage: ${GREEN}${VOLTAGE}${NC}"
else
    echo -e "${YELLOW}vcgencmd not available${NC}"
fi

CPU_USAGE=$(top -bn1 | grep "Cpu(s)" | sed "s/.*, *\([0-9.]*\)%* id.*/\1/" | awk '{print 100 - $1"%"}')
echo -e "CPU Usage: ${GREEN}${CPU_USAGE}${NC}"

CPU_LOAD=$(uptime | awk -F'load average:' '{print $2}')
echo -e "Load Average: ${GREEN}${CPU_LOAD}${NC}"
echo ""

# Memory Information
echo -e "${CYAN}=== Memory Information ===${NC}"
free -h | grep -E "Mem|Swap" | while read line; do
    echo -e "${GREEN}${line}${NC}"
done

# Check if swap is being used
SWAP_USED=$(free -m | awk '/^Swap:/{print $3}')
if [ "$SWAP_USED" -gt 0 ]; then
    echo -e "${YELLOW}Warning: Swap is being used (${SWAP_USED}MB)${NC}"
fi
echo ""

# Disk Information
echo -e "${CYAN}=== Disk Information ===${NC}"
df -h / | tail -1 | awk '{printf "Root: %s used of %s (%s)\n", $3, $2, $5}' | sed "s/\(.*\)/${GREEN}\1${NC}/"

# Check disk space
DISK_USAGE=$(df / | tail -1 | awk '{print $5}' | sed 's/%//')
if [ "$DISK_USAGE" -gt 90 ]; then
    echo -e "${RED}Warning: Disk usage is above 90%${NC}"
elif [ "$DISK_USAGE" -gt 80 ]; then
    echo -e "${YELLOW}Warning: Disk usage is above 80%${NC}"
fi
echo ""

# Docker Information
echo -e "${CYAN}=== Docker Information ===${NC}"
if command -v docker &> /dev/null; then
    DOCKER_VERSION=$(docker --version)
    echo -e "Version: ${GREEN}${DOCKER_VERSION}${NC}"

    if docker ps | grep -q minecraft-server; then
        echo -e "Minecraft Container: ${GREEN}Running${NC}"
        echo ""
        echo -e "${CYAN}Container Stats:${NC}"
        docker stats --no-stream minecraft-server --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}\t{{.BlockIO}}"
    else
        echo -e "Minecraft Container: ${RED}Not Running${NC}"
    fi
else
    echo -e "${YELLOW}Docker not installed${NC}"
fi
echo ""

# Network Information
echo -e "${CYAN}=== Network Information ===${NC}"
if command -v ifconfig &> /dev/null; then
    INTERFACES=$(ifconfig | grep -E "^[a-z]" | awk '{print $1}' | sed 's/:$//')
    for iface in $INTERFACES; do
        if [ "$iface" != "lo" ]; then
            IP=$(ifconfig "$iface" | grep "inet " | awk '{print $2}')
            if [ -n "$IP" ]; then
                RX=$(ifconfig "$iface" | grep "RX packets" | awk '{print $5}')
                TX=$(ifconfig "$iface" | grep "TX packets" | awk '{print $5}')
                echo -e "${GREEN}${iface}:${NC} ${IP}"
                echo -e "  RX: ${GREEN}${RX}${NC}, TX: ${GREEN}${TX}${NC}"
            fi
        fi
    done
fi
echo ""

# Minecraft Server Status
echo -e "${CYAN}=== Minecraft Server Status ===${NC}"
if [ -f "$HOME/minecraft-server/scripts/manage.sh" ]; then
    cd "$HOME/minecraft-server" || exit 1
    ./scripts/manage.sh status 2>/dev/null || echo -e "${YELLOW}Could not determine server status${NC}"
else
    echo -e "${YELLOW}Minecraft server directory not found${NC}"
fi
echo ""

# Performance Warnings
echo -e "${CYAN}=== Performance Warnings ===${NC}"
WARNINGS=0

# Check temperature
if command -v vcgencmd &> /dev/null; then
    TEMP=$(vcgencmd measure_temp | cut -d= -f2 | cut -d\' -f1)
    if (( $(echo "$TEMP > 80" | bc -l) )); then
        echo -e "${RED}⚠ High CPU temperature: ${TEMP}°C${NC}"
        WARNINGS=$((WARNINGS + 1))
    elif (( $(echo "$TEMP > 70" | bc -l) )); then
        echo -e "${YELLOW}⚠ Elevated CPU temperature: ${TEMP}°C${NC}"
        WARNINGS=$((WARNINGS + 1))
    fi
fi

# Check memory
MEM_USAGE=$(free | grep Mem | awk '{printf "%.0f", $3/$2 * 100}')
if [ "$MEM_USAGE" -gt 90 ]; then
    echo -e "${RED}⚠ High memory usage: ${MEM_USAGE}%${NC}"
    WARNINGS=$((WARNINGS + 1))
elif [ "$MEM_USAGE" -gt 80 ]; then
    echo -e "${YELLOW}⚠ Elevated memory usage: ${MEM_USAGE}%${NC}"
    WARNINGS=$((WARNINGS + 1))
fi

# Check disk
if [ "$DISK_USAGE" -gt 90 ]; then
    echo -e "${RED}⚠ High disk usage: ${DISK_USAGE}%${NC}"
    WARNINGS=$((WARNINGS + 1))
fi

# Check swap
if [ "$SWAP_USED" -gt 100 ]; then
    echo -e "${RED}⚠ Significant swap usage: ${SWAP_USED}MB${NC}"
    WARNINGS=$((WARNINGS + 1))
fi

if [ $WARNINGS -eq 0 ]; then
    echo -e "${GREEN}✓ No performance warnings${NC}"
fi
echo ""

echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}Monitor complete${NC}"
echo -e "${BLUE}========================================${NC}"

