#!/bin/bash
# Script to check and update Docker image to latest version

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

IMAGE_NAME="ghcr.io/and3rn3t/minecraft-server:latest"

echo -e "${BLUE}=== Docker Image Update Check ===${NC}\n"

# Check if docker-compose.yml exists
if [ ! -f "$PROJECT_DIR/docker-compose.yml" ]; then
    echo -e "${RED}Error: docker-compose.yml not found${NC}"
    echo -e "${YELLOW}Make sure you're in the project directory${NC}"
    exit 1
fi

# Check current image
echo -e "${BLUE}Checking current image...${NC}"
CURRENT_IMAGE=$(docker inspect minecraft-server --format='{{.Config.Image}}' 2>/dev/null || echo "not running")
echo -e "Current container image: ${CURRENT_IMAGE}"

# Check if using registry image
if grep -q "image:" "$PROJECT_DIR/docker-compose.yml" && ! grep -q "build:" "$PROJECT_DIR/docker-compose.yml"; then
    echo -e "${GREEN}✓ Using registry-based image${NC}"
else
    echo -e "${YELLOW}⚠ Using local build. Consider switching to registry image for updates.${NC}"
    echo -e "${YELLOW}  See: docker-compose.registry.yml${NC}"
fi

# Pull latest image
echo -e "\n${BLUE}Pulling latest image from registry...${NC}"
cd "$PROJECT_DIR" || exit 1

if docker compose pull; then
    echo -e "${GREEN}✓ Image pull completed${NC}"
else
    echo -e "${RED}✗ Failed to pull image${NC}"
    echo -e "${YELLOW}Check authentication: docker login ghcr.io${NC}"
    exit 1
fi

# Check if update is needed
echo -e "\n${BLUE}Checking if update is needed...${NC}"
if docker compose up -d --dry-run 2>&1 | grep -q "would be created\|would be recreated"; then
    echo -e "${YELLOW}⚠ New image available!${NC}"

    # Ask for confirmation
    read -p "Update container now? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${BLUE}Updating container...${NC}"
        docker compose up -d --force-recreate

        echo -e "\n${GREEN}✓ Container updated!${NC}"
        echo -e "${BLUE}Checking status...${NC}"
        sleep 2
        docker ps | grep minecraft-server || echo -e "${YELLOW}Container may be starting...${NC}"
    else
        echo -e "${YELLOW}Update cancelled. Run 'docker compose up -d --force-recreate' when ready.${NC}"
    fi
else
    echo -e "${GREEN}✓ Already using latest image${NC}"
fi

# Show current status
echo -e "\n${BLUE}=== Current Status ===${NC}"
docker ps --filter "name=minecraft-server" --format "table {{.Names}}\t{{.Status}}\t{{.Image}}"

echo -e "\n${BLUE}Done!${NC}"

