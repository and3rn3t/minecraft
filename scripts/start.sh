#!/bin/bash
# Minecraft Server Startup Script for Raspberry Pi 5
#
# Runs as PID 1 inside the container. Java is exec'd at the end so it receives
# SIGTERM directly and can shut the world down cleanly on `docker stop`.

set -uo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting Minecraft Server for Raspberry Pi 5${NC}"

# Set default values
MINECRAFT_VERSION=${MINECRAFT_VERSION:-1.20.4}
SERVER_TYPE=${SERVER_TYPE:-vanilla}
MEMORY_MIN=${MEMORY_MIN:-1G}
MEMORY_MAX=${MEMORY_MAX:-2G}
SERVER_PORT=${SERVER_PORT:-25565}

SERVER_DIR="/minecraft/server"
DOWNLOADER="/minecraft/scripts/download-server.sh"

# Determine jar filename based on server type. These names match the output
# filenames that download-server.sh writes.
case "$SERVER_TYPE" in
    paper)
        MINECRAFT_JAR="paper-${MINECRAFT_VERSION}.jar"
        ;;
    fabric)
        MINECRAFT_JAR="fabric-server.jar"
        ;;
    spigot)
        MINECRAFT_JAR="spigot.jar"
        ;;
    vanilla | *)
        MINECRAFT_JAR="server.jar"
        ;;
esac

# Fall back to a plain server.jar if the type-specific jar was never placed
if [ ! -f "${SERVER_DIR}/${MINECRAFT_JAR}" ] && [ -f "${SERVER_DIR}/server.jar" ]; then
    echo -e "${YELLOW}${MINECRAFT_JAR} not found, falling back to server.jar${NC}"
    MINECRAFT_JAR="server.jar"
fi

# Create the directories the server writes to. Ownership is handled by the
# image (and by scripts/fix-permissions.sh on the host for bind mounts); this
# script deliberately does not widen permissions on the world data.
mkdir -p "${SERVER_DIR}/logs" "${SERVER_DIR}/world" /minecraft/backups

if [ ! -w "$SERVER_DIR" ]; then
    echo -e "${RED}${SERVER_DIR} is not writable by $(id -un).${NC}"
    echo -e "${YELLOW}On the host, run: ./scripts/fix-permissions.sh${NC}"
    exit 1
fi

# Check if EULA is accepted
if [ ! -f "${SERVER_DIR}/eula.txt" ] || ! grep -q "eula=true" "${SERVER_DIR}/eula.txt"; then
    echo -e "${YELLOW}EULA not accepted. Creating eula.txt...${NC}"
    echo "eula=true" > "${SERVER_DIR}/eula.txt"
fi

# Download the server jar for the requested version if it is not present.
# download-server.sh resolves the real download URL from Mojang's version
# manifest (and the Paper/Fabric APIs), so MINECRAFT_VERSION is honoured.
if [ ! -f "${SERVER_DIR}/${MINECRAFT_JAR}" ]; then
    echo -e "${YELLOW}Downloading ${SERVER_TYPE} server ${MINECRAFT_VERSION}...${NC}"

    if [ ! -x "$DOWNLOADER" ]; then
        echo -e "${RED}Downloader not found at ${DOWNLOADER}${NC}"
        echo -e "${YELLOW}Place a server jar at ${SERVER_DIR}/${MINECRAFT_JAR} and restart.${NC}"
        exit 1
    fi

    if ! "$DOWNLOADER" --type "$SERVER_TYPE" --version "$MINECRAFT_VERSION" --output "$SERVER_DIR"; then
        echo -e "${RED}Failed to download ${SERVER_TYPE} server ${MINECRAFT_VERSION}${NC}"
        exit 1
    fi

    echo -e "${GREEN}Download complete!${NC}"
fi

if [ ! -f "${SERVER_DIR}/${MINECRAFT_JAR}" ]; then
    echo -e "${RED}Server jar ${MINECRAFT_JAR} is missing after download${NC}"
    exit 1
fi

# A stale session.lock from an unclean shutdown stops the world from loading
rm -f "${SERVER_DIR}/world/session.lock" 2>/dev/null || true

# Display server information
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Minecraft Server Configuration${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e "Type:    ${SERVER_TYPE}"
echo -e "Version: ${MINECRAFT_VERSION}"
echo -e "Jar:     ${MINECRAFT_JAR}"
echo -e "Memory:  ${MEMORY_MIN} - ${MEMORY_MAX}"
echo -e "Port:    ${SERVER_PORT}"
echo -e "${GREEN}========================================${NC}"

# Start the server
echo -e "${GREEN}Starting Minecraft Server...${NC}"
cd "$SERVER_DIR" || exit 1

# Aikar's flags, tuned for G1GC on a small heap
exec java -Xms"${MEMORY_MIN}" -Xmx"${MEMORY_MAX}" \
    -XX:+UseG1GC \
    -XX:+ParallelRefProcEnabled \
    -XX:MaxGCPauseMillis=200 \
    -XX:+UnlockExperimentalVMOptions \
    -XX:+DisableExplicitGC \
    -XX:+AlwaysPreTouch \
    -XX:+UseStringDeduplication \
    -XX:+OptimizeStringConcat \
    -XX:+UseCompressedOops \
    -XX:+UseCompressedClassPointers \
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
    -XX:+UseTransparentHugePages \
    -XX:MaxTenuringThreshold=1 \
    -Djava.security.egd=file:/dev/urandom \
    -Dusing.aikars.flags=https://mcflags.emc.gs \
    -Daikars.new.flags=true \
    -jar "${MINECRAFT_JAR}" \
    --nogui
