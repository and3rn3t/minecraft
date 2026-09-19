#!/bin/bash
# Health check script for all Minecraft server components
# Checks if Minecraft server, API server, and web server are running

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

# Configuration
API_PORT=8080
WEB_PORT=80
MINECRAFT_PORT=25565

# Status tracking
ALL_OK=true

echo -e "${BLUE}=== Minecraft Server Component Health Check ===${NC}\n"

# Check Minecraft server (Docker container)
echo -e "${BLUE}Checking Minecraft server...${NC}"
if docker ps --format '{{.Names}}' | grep -q "^minecraft-server$"; then
    CONTAINER_STATUS=$(docker inspect --format='{{.State.Status}}' minecraft-server 2>/dev/null || echo "not found")
    if [ "$CONTAINER_STATUS" = "running" ]; then
        echo -e "${GREEN}✓ Minecraft server container is running${NC}"

        # Check if port is listening
        if netstat -tuln 2>/dev/null | grep -q ":$MINECRAFT_PORT " || ss -tuln 2>/dev/null | grep -q ":$MINECRAFT_PORT "; then
            echo -e "${GREEN}✓ Minecraft server port $MINECRAFT_PORT is listening${NC}"
        else
            echo -e "${YELLOW}⚠ Minecraft server port $MINECRAFT_PORT is not listening${NC}"
            ALL_OK=false
        fi
    else
        echo -e "${RED}✗ Minecraft server container is not running (status: $CONTAINER_STATUS)${NC}"
        ALL_OK=false
    fi
else
    echo -e "${RED}✗ Minecraft server container is not running${NC}"
    ALL_OK=false
fi
echo ""

# Check API server
echo -e "${BLUE}Checking API server...${NC}"
if systemctl is-active --quiet minecraft-api.service 2>/dev/null; then
    echo -e "${GREEN}✓ API server systemd service is active${NC}"

    # Check if API is responding
    if curl -s -f -o /dev/null "http://127.0.0.1:$API_PORT/api/status" 2>/dev/null; then
        echo -e "${GREEN}✓ API server is responding on port $API_PORT${NC}"
    else
        echo -e "${YELLOW}⚠ API server service is active but not responding on port $API_PORT${NC}"
        ALL_OK=false
    fi
else
    # Fallback: check if process is running
    if pgrep -f "python.*server.py" > /dev/null 2>&1; then
        echo -e "${YELLOW}⚠ API server process is running but systemd service is not active${NC}"
        if curl -s -f -o /dev/null "http://127.0.0.1:$API_PORT/api/status" 2>/dev/null; then
            echo -e "${GREEN}✓ API server is responding on port $API_PORT${NC}"
        else
            echo -e "${RED}✗ API server is not responding on port $API_PORT${NC}"
            ALL_OK=false
        fi
    else
        echo -e "${RED}✗ API server is not running${NC}"
        ALL_OK=false
    fi
fi
echo ""

# Check web server (nginx)
echo -e "${BLUE}Checking web server...${NC}"
if systemctl is-active --quiet nginx 2>/dev/null; then
    echo -e "${GREEN}✓ Nginx service is active${NC}"

    # Check if web interface is accessible
    if curl -s -f -o /dev/null "http://127.0.0.1:$WEB_PORT" 2>/dev/null; then
        echo -e "${GREEN}✓ Web interface is accessible on port $WEB_PORT${NC}"
    else
        echo -e "${YELLOW}⚠ Nginx is running but web interface is not accessible${NC}"
        ALL_OK=false
    fi
else
    echo -e "${RED}✗ Nginx service is not running${NC}"
    ALL_OK=false
fi
echo ""

# Check if web build exists
if [ -d "$PROJECT_DIR/web/dist" ] && [ -f "$PROJECT_DIR/web/dist/index.html" ]; then
    echo -e "${GREEN}✓ Web interface build files exist${NC}"
else
    echo -e "${YELLOW}⚠ Web interface build files not found (run: cd web && npm run build)${NC}"
    ALL_OK=false
fi
echo ""

# Summary
echo -e "${BLUE}=== Summary ===${NC}"
if [ "$ALL_OK" = true ]; then
    echo -e "${GREEN}✓ All components are running correctly!${NC}"
    exit 0
else
    echo -e "${RED}✗ Some components are not running correctly${NC}"
    echo -e "${YELLOW}Run the following to start services:${NC}"
    echo -e "  sudo systemctl start minecraft.service"
    echo -e "  sudo systemctl start minecraft-api.service"
    echo -e "  sudo systemctl start minecraft-web.service"
    exit 1
fi

