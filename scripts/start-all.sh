#!/bin/bash
# Start all Minecraft server components
# Starts API server, web server, and Minecraft server

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}Starting all Minecraft server components...${NC}\n"

# Start API server
echo -e "${BLUE}Starting API server...${NC}"
if sudo systemctl start minecraft-api.service 2>/dev/null; then
    echo -e "${GREEN}✓ API server started${NC}"
else
    echo -e "${YELLOW}⚠ API server may already be running or systemd service not installed${NC}"
    echo -e "${YELLOW}  Try: ./scripts/api-server.sh start${NC}"
fi

# Start web server (nginx)
echo -e "${BLUE}Starting web server...${NC}"
if sudo systemctl start minecraft-web.service 2>/dev/null; then
    echo -e "${GREEN}✓ Web server started${NC}"
else
    echo -e "${YELLOW}⚠ Web server may already be running or systemd service not installed${NC}"
    echo -e "${YELLOW}  Try: sudo systemctl start nginx${NC}"
fi

# Start Minecraft server
echo -e "${BLUE}Starting Minecraft server...${NC}"
if sudo systemctl start minecraft.service 2>/dev/null; then
    echo -e "${GREEN}✓ Minecraft server started${NC}"
else
    echo -e "${YELLOW}⚠ Minecraft server may already be running or systemd service not installed${NC}"
    echo -e "${YELLOW}  Try: ./scripts/manage.sh start${NC}"
fi

echo -e "\n${BLUE}Checking service status...${NC}"
sleep 2

# Run health check
if [ -f "scripts/check-services.sh" ]; then
    ./scripts/check-services.sh
else
    echo -e "${YELLOW}Health check script not found${NC}"
fi

