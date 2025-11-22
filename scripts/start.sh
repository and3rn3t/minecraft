#!/bin/bash
# Minecraft Server Startup Script for Raspberry Pi 5

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting Minecraft Server for Raspberry Pi 5${NC}"

# Set default values
MINECRAFT_VERSION=${MINECRAFT_VERSION:-1.20.4}
MINECRAFT_JAR=${MINECRAFT_JAR:-server.jar}
MEMORY_MIN=${MEMORY_MIN:-1G}
MEMORY_MAX=${MEMORY_MAX:-2G}
SERVER_PORT=${SERVER_PORT:-25565}

# Check if EULA is accepted
if [ ! -f "/minecraft/server/eula.txt" ] || ! grep -q "eula=true" "/minecraft/server/eula.txt"; then
    echo -e "${YELLOW}EULA not accepted. Creating eula.txt...${NC}"
    echo "eula=true" > /minecraft/server/eula.txt
fi

# Download server jar if it doesn't exist
if [ ! -f "/minecraft/server/${MINECRAFT_JAR}" ]; then
    echo -e "${YELLOW}Downloading Minecraft Server ${MINECRAFT_VERSION}...${NC}"
    DOWNLOAD_URL="https://piston-data.mojang.com/v1/objects/8dd1a28015f51b1803213892b50b7b4fc76e594d/server.jar"
    
    # For version 1.20.4 - update this URL for different versions
    # You can find the correct URL at https://www.minecraft.net/en-us/download/server
    
    wget -O "/minecraft/server/${MINECRAFT_JAR}" "${DOWNLOAD_URL}" || {
        echo -e "${RED}Failed to download Minecraft server jar${NC}"
        exit 1
    }
    
    echo -e "${GREEN}Download complete!${NC}"
fi

# Create necessary directories
mkdir -p /minecraft/server/logs
mkdir -p /minecraft/server/world
mkdir -p /minecraft/backups

# Display server information
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Minecraft Server Configuration${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e "Version: ${MINECRAFT_VERSION}"
echo -e "Memory: ${MEMORY_MIN} - ${MEMORY_MAX}"
echo -e "Port: ${SERVER_PORT}"
echo -e "${GREEN}========================================${NC}"

# Start the server
echo -e "${GREEN}Starting Minecraft Server...${NC}"
cd /minecraft/server

exec java -Xms${MEMORY_MIN} -Xmx${MEMORY_MAX} \
    -XX:+UseG1GC \
    -XX:+ParallelRefProcEnabled \
    -XX:MaxGCPauseMillis=200 \
    -XX:+UnlockExperimentalVMOptions \
    -XX:+DisableExplicitGC \
    -XX:+AlwaysPreTouch \
    -XX:G1NewSizePercent=30 \
    -XX:G1MaxNewSizePercent=40 \
    -XX:G1HeapRegionSize=8M \
    -XX:G1ReservePercent=20 \
    -XX:G1HeapWastePercent=5 \
    -XX:G1MixedGCCountTarget=4 \
    -XX:InitiatingHeapOccupancyPercent=15 \
    -XX:G1MixedGCLiveThresholdPercent=90 \
    -XX:G1RSetUpdatingPauseTimePercent=5 \
    -XX:SurvivorRatio=32 \
    -XX:+PerfDisableSharedMem \
    -XX:MaxTenuringThreshold=1 \
    -Dusing.aikars.flags=https://mcflags.emc.gs \
    -Daikars.new.flags=true \
    -jar ${MINECRAFT_JAR} \
    --nogui
