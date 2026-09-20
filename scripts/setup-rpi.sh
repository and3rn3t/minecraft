#!/bin/bash
# Raspberry Pi 5 Setup Script for Minecraft Server
# Run this script on your Raspberry Pi 5 after first boot

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Minecraft Server Setup for Raspberry Pi 5${NC}"
echo -e "${BLUE}========================================${NC}"

# Check if running on Raspberry Pi
if [ ! -f /proc/device-tree/model ]; then
    echo -e "${YELLOW}Warning: This script is designed for Raspberry Pi${NC}"
fi

# Update system
echo -e "${GREEN}[1/9] Updating system packages...${NC}"
sudo apt-get update
sudo apt-get upgrade -y

# Install Docker
echo -e "${GREEN}[2/9] Installing Docker...${NC}"
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    rm get-docker.sh
    echo -e "${GREEN}Docker installed successfully${NC}"
else
    echo -e "${YELLOW}Docker is already installed${NC}"
fi

# Install Docker Compose
echo -e "${GREEN}[3/9] Installing Docker Compose...${NC}"
if ! docker compose version &> /dev/null && ! command -v docker-compose &> /dev/null; then
    # Compose v1 reached end of life in July 2023; install the v2 plugin
    sudo apt-get install -y docker-compose-plugin
    echo -e "${GREEN}Docker Compose installed successfully${NC}"
else
    echo -e "${YELLOW}Docker Compose is already installed${NC}"
fi

# Install additional utilities
echo -e "${GREEN}[4/9] Installing additional utilities...${NC}"
sudo apt-get install -y git wget curl screen htop python3 python3-pip python3-venv

# Install Node.js for web interface (if not already installed)
if ! command -v node &> /dev/null; then
    echo -e "${GREEN}Installing Node.js...${NC}"
    curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
    sudo apt-get install -y nodejs
    echo -e "${GREEN}Node.js installed successfully${NC}"
else
    echo -e "${YELLOW}Node.js is already installed ($(node --version))${NC}"
fi

# Clone or update repository
echo -e "${GREEN}[5/9] Setting up Minecraft server files...${NC}"
MINECRAFT_DIR="$HOME/minecraft-server"
if [ ! -d "$MINECRAFT_DIR" ]; then
    mkdir -p "$MINECRAFT_DIR"
    echo -e "${GREEN}Created minecraft server directory at $MINECRAFT_DIR${NC}"
fi

# Create data directories
mkdir -p "$MINECRAFT_DIR/data"
mkdir -p "$MINECRAFT_DIR/backups"
mkdir -p "$MINECRAFT_DIR/plugins"

# Setup Python API dependencies (optional, for API server)
echo -e "${GREEN}[6/9] Setting up Python API dependencies...${NC}"
if [ -d "$MINECRAFT_DIR/api" ]; then
    cd "$MINECRAFT_DIR/api"
    if [ ! -d "venv" ]; then
        python3 -m venv venv
    fi
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    echo -e "${GREEN}Python API dependencies installed${NC}"
    cd "$HOME"
else
    echo -e "${YELLOW}API directory not found, skipping Python dependencies${NC}"
fi

# Setup Node.js web interface dependencies (optional, for web interface)
echo -e "${GREEN}[7/9] Setting up Node.js web interface dependencies...${NC}"
if [ -d "$MINECRAFT_DIR/web" ]; then
    cd "$MINECRAFT_DIR/web"
    if [ -f "package.json" ]; then
        npm install
        echo -e "${GREEN}Web interface dependencies installed${NC}"
    else
        echo -e "${YELLOW}package.json not found, skipping web dependencies${NC}"
    fi
    cd "$HOME"
else
    echo -e "${YELLOW}Web directory not found, skipping web dependencies${NC}"
fi

# Enable Docker service
echo -e "${GREEN}[8/9] Enabling Docker service...${NC}"
sudo systemctl enable docker
sudo systemctl start docker

# System-level tuning (CPU governor, swap, sysctl, journald, USB power, TRIM).
# Separate from the packages/deps above because it edits system config and
# offers a reboot, so it is opt-in rather than silently applied.
echo -e "${GREEN}[9/9] Raspberry Pi system-level optimizations...${NC}"
if [ -f /proc/device-tree/model ]; then
    read -p "Apply system-level performance tuning now (CPU governor, swap, sysctl, journald)? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        "${SCRIPT_DIR}/optimize-rpi5.sh"
    else
        echo -e "${YELLOW}Skipped. Run ${SCRIPT_DIR}/optimize-rpi5.sh later to apply it.${NC}"
    fi
else
    echo -e "${YELLOW}Not running on a Raspberry Pi; skipping system-level tuning.${NC}"
fi

echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}Setup Complete!${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e ""
echo -e "${YELLOW}Next Steps:${NC}"
echo -e "1. Copy the Minecraft server files to: ${MINECRAFT_DIR}"
echo -e "2. Navigate to the directory: cd ${MINECRAFT_DIR}"
echo -e "3. Start the server: docker compose up -d"
echo -e "4. View logs: docker compose logs -f"
echo -e "5. Stop the server: docker compose down"
echo -e ""
echo -e "${YELLOW}Note: You may need to log out and back in for Docker permissions to take effect${NC}"
echo -e "${BLUE}========================================${NC}"
