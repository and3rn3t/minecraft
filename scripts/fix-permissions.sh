#!/bin/bash
# Fix permissions for Minecraft server directories
# Run this script on the host to fix permission issues with Docker volumes

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo -e "${GREEN}Fixing permissions for Minecraft server directories...${NC}"

# Check if directories exist
if [ ! -d "$PROJECT_DIR/data" ]; then
    echo -e "${YELLOW}Creating data directory...${NC}"
    mkdir -p "$PROJECT_DIR/data"
fi

if [ ! -d "$PROJECT_DIR/backups" ]; then
    echo -e "${YELLOW}Creating backups directory...${NC}"
    mkdir -p "$PROJECT_DIR/backups"
fi

if [ ! -d "$PROJECT_DIR/plugins" ]; then
    echo -e "${YELLOW}Creating plugins directory...${NC}"
    mkdir -p "$PROJECT_DIR/plugins"
fi

# Fix permissions - make directories world-writable so Docker container can write
echo -e "${GREEN}Setting permissions...${NC}"

# Make directories writable
chmod -R 777 "$PROJECT_DIR/data" 2>/dev/null || {
    echo -e "${RED}Failed to set permissions for data directory${NC}"
    echo -e "${YELLOW}You may need to run with sudo: sudo $0${NC}"
    exit 1
}

chmod -R 777 "$PROJECT_DIR/backups" 2>/dev/null || {
    echo -e "${YELLOW}Warning: Could not set permissions for backups directory${NC}"
}

chmod -R 777 "$PROJECT_DIR/plugins" 2>/dev/null || {
    echo -e "${YELLOW}Warning: Could not set permissions for plugins directory${NC}"
}

# Remove any session.lock files that might be blocking
if [ -f "$PROJECT_DIR/data/world/session.lock" ]; then
    echo -e "${YELLOW}Removing session.lock file...${NC}"
    rm -f "$PROJECT_DIR/data/world/session.lock"
fi

# Fix permissions for specific files
if [ -f "$PROJECT_DIR/data/server.properties" ]; then
    chmod 666 "$PROJECT_DIR/data/server.properties"
fi

if [ -f "$PROJECT_DIR/data/eula.txt" ]; then
    chmod 666 "$PROJECT_DIR/data/eula.txt"
fi

echo -e "${GREEN}Permissions fixed!${NC}"
echo -e "${GREEN}You can now restart the server:${NC}"
echo -e "  docker-compose restart"
echo -e "  or"
echo -e "  ./manage.sh restart"

