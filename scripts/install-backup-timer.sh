#!/bin/bash
# Installation script for systemd backup timer

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
SYSTEMD_DIR="${PROJECT_DIR}/systemd"
SERVICE_FILE="${SYSTEMD_DIR}/minecraft-backup.service"
TIMER_FILE="${SYSTEMD_DIR}/minecraft-backup.timer"

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo -e "${RED}Error: Do not run this script as root${NC}"
    echo -e "${YELLOW}The service will run as your user account${NC}"
    exit 1
fi

# Get current user
CURRENT_USER=$(whoami)
USER_HOME=$(eval echo ~$CURRENT_USER)

# Check if files exist
if [ ! -f "$SERVICE_FILE" ]; then
    echo -e "${RED}Error: Service file not found: $SERVICE_FILE${NC}"
    exit 1
fi

if [ ! -f "$TIMER_FILE" ]; then
    echo -e "${RED}Error: Timer file not found: $TIMER_FILE${NC}"
    exit 1
fi

echo -e "${BLUE}Installing Minecraft backup timer...${NC}"

# Update service file with actual user and paths
TEMP_SERVICE=$(mktemp)
sed "s|%i|$CURRENT_USER|g; s|/home/%i/minecraft-server|$PROJECT_DIR|g" "$SERVICE_FILE" > "$TEMP_SERVICE"

# Copy files to systemd directory
echo -e "${YELLOW}Copying systemd files...${NC}"
sudo cp "$TEMP_SERVICE" /etc/systemd/system/minecraft-backup.service
sudo cp "$TIMER_FILE" /etc/systemd/system/minecraft-backup.timer
rm -f "$TEMP_SERVICE"

# Reload systemd
echo -e "${YELLOW}Reloading systemd daemon...${NC}"
sudo systemctl daemon-reload

# Enable and start timer
echo -e "${YELLOW}Enabling backup timer...${NC}"
sudo systemctl enable minecraft-backup.timer
sudo systemctl start minecraft-backup.timer

# Show status
echo -e "${GREEN}Backup timer installed successfully!${NC}"
echo -e ""
echo -e "${BLUE}Timer status:${NC}"
sudo systemctl status minecraft-backup.timer --no-pager -l

echo -e ""
echo -e "${BLUE}Useful commands:${NC}"
echo -e "  View timer status: ${GREEN}sudo systemctl status minecraft-backup.timer${NC}"
echo -e "  View service logs: ${GREEN}sudo journalctl -u minecraft-backup.service${NC}"
echo -e "  Stop timer: ${GREEN}sudo systemctl stop minecraft-backup.timer${NC}"
echo -e "  Start timer: ${GREEN}sudo systemctl start minecraft-backup.timer${NC}"
echo -e "  Disable timer: ${GREEN}sudo systemctl disable minecraft-backup.timer${NC}"

