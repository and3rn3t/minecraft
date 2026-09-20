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
echo -e "${GREEN}[1/11] Updating system packages...${NC}"
sudo apt-get update
sudo apt-get upgrade -y

# Install Docker
echo -e "${GREEN}[2/11] Installing Docker...${NC}"
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
echo -e "${GREEN}[3/11] Installing Docker Compose...${NC}"
if ! docker compose version &> /dev/null && ! command -v docker-compose &> /dev/null; then
    # Compose v1 reached end of life in July 2023; install the v2 plugin
    sudo apt-get install -y docker-compose-plugin
    echo -e "${GREEN}Docker Compose installed successfully${NC}"
else
    echo -e "${YELLOW}Docker Compose is already installed${NC}"
fi

# Install additional utilities
echo -e "${GREEN}[4/11] Installing additional utilities...${NC}"
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

# Create the directory the server files (copied here separately, not by this
# script) and runtime data will live in.
echo -e "${GREEN}[5/11] Setting up Minecraft server files...${NC}"
MINECRAFT_DIR="$HOME/minecraft-server"
if [ ! -d "$MINECRAFT_DIR" ]; then
    mkdir -p "$MINECRAFT_DIR"
    echo -e "${GREEN}Created minecraft server directory at $MINECRAFT_DIR${NC}"
fi

# Create data directories
mkdir -p "$MINECRAFT_DIR/data"
mkdir -p "$MINECRAFT_DIR/backups"
mkdir -p "$MINECRAFT_DIR/plugins"

# Size MEMORY_MIN/MEMORY_MAX/CONTAINER_MEMORY_LIMIT to this Pi's RAM instead
# of leaving the 4GB-board defaults in place on an 8GB board (or vice versa).
# docs/INSTALL.md has the repo cloned into $MINECRAFT_DIR before this script
# runs, so .env.example is already here; an existing .env is left untouched.
echo -e "${GREEN}[6/11] Configuring .env for detected RAM...${NC}"
ENV_FILE="$MINECRAFT_DIR/.env"
ENV_EXAMPLE="$MINECRAFT_DIR/.env.example"
if [ -f "$ENV_FILE" ]; then
    echo -e "${YELLOW}${ENV_FILE} already exists; leaving it as-is.${NC}"
elif [ -f "$ENV_EXAMPLE" ]; then
    TOTAL_RAM_MB=$(free -m | awk '/^Mem:/{print $2}')
    if [ "$TOTAL_RAM_MB" -lt 6144 ]; then
        MEM_MIN=1G
        MEM_MAX=2G
        MEM_LIMIT=3G
        PI_SIZE="4GB"
    else
        MEM_MIN=2G
        MEM_MAX=4G
        MEM_LIMIT=5G
        PI_SIZE="8GB"
    fi
    cp "$ENV_EXAMPLE" "$ENV_FILE"
    sed -i.bak "s/^MEMORY_MIN=.*/MEMORY_MIN=${MEM_MIN}/" "$ENV_FILE"
    sed -i.bak "s/^MEMORY_MAX=.*/MEMORY_MAX=${MEM_MAX}/" "$ENV_FILE"
    sed -i.bak "s/^CONTAINER_MEMORY_LIMIT=.*/CONTAINER_MEMORY_LIMIT=${MEM_LIMIT}/" "$ENV_FILE"
    rm -f "${ENV_FILE}.bak"
    echo -e "${GREEN}Created .env (detected ~${PI_SIZE} Pi): MEMORY_MIN=${MEM_MIN} MEMORY_MAX=${MEM_MAX} CONTAINER_MEMORY_LIMIT=${MEM_LIMIT}${NC}"
    echo -e "${YELLOW}Review ${ENV_FILE}, or run 'make perf-preset' for a different profile.${NC}"
else
    echo -e "${YELLOW}${ENV_EXAMPLE} not found; copy it to .env manually before starting the server.${NC}"
fi

# Setup Python API dependencies (optional, for API server)
echo -e "${GREEN}[7/11] Setting up Python API dependencies...${NC}"
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

# Without a persistent SECRET_KEY, api/server.py generates a random one on
# every process start (it says so itself in a startup warning), which
# silently invalidates every login session and the Logs/Console WebSocket
# (both authenticate with a JWT) on every restart — including routine
# updates and crash-restarts, not just reinstalls.
echo -e "${GREEN}[8/11] Configuring persistent API secret key...${NC}"
API_CONF_FILE="$MINECRAFT_DIR/config/api.conf"
API_CONF_EXAMPLE="$MINECRAFT_DIR/config/api.conf.example"
if [ -f "$API_CONF_FILE" ] && grep -q "^SECRET_KEY=." "$API_CONF_FILE" 2>/dev/null; then
    echo -e "${YELLOW}${API_CONF_FILE} already has a SECRET_KEY; leaving it as-is.${NC}"
elif command -v python3 &> /dev/null; then
    mkdir -p "$(dirname "$API_CONF_FILE")"
    if [ ! -f "$API_CONF_FILE" ] && [ -f "$API_CONF_EXAMPLE" ]; then
        cp "$API_CONF_EXAMPLE" "$API_CONF_FILE"
    fi
    GENERATED_SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    if grep -q "^SECRET_KEY=" "$API_CONF_FILE" 2>/dev/null; then
        sed -i.bak "s/^SECRET_KEY=.*/SECRET_KEY=${GENERATED_SECRET}/" "$API_CONF_FILE"
        rm -f "${API_CONF_FILE}.bak"
    else
        echo "SECRET_KEY=${GENERATED_SECRET}" >> "$API_CONF_FILE"
    fi
    chmod 600 "$API_CONF_FILE"
    echo -e "${GREEN}Generated a persistent SECRET_KEY in ${API_CONF_FILE}${NC}"
else
    echo -e "${YELLOW}python3 not found; set SECRET_KEY in ${API_CONF_FILE} manually.${NC}"
fi

# Setup Node.js web interface dependencies (optional, for web interface)
echo -e "${GREEN}[9/11] Setting up Node.js web interface dependencies...${NC}"
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
echo -e "${GREEN}[10/11] Enabling Docker service...${NC}"
sudo systemctl enable docker
sudo systemctl start docker

# System-level tuning (CPU governor, swap, sysctl, journald, USB power, TRIM).
# Separate from the packages/deps above because it edits system config and
# offers a reboot, so it is opt-in rather than silently applied.
echo -e "${GREEN}[11/11] Raspberry Pi system-level optimizations...${NC}"
if [ -f /proc/device-tree/model ]; then
    read -p "Apply system-level performance tuning now (CPU governor, swap, sysctl, journald)? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        if [ -f "${SCRIPT_DIR}/optimize-rpi5.sh" ]; then
            # Invoked via bash rather than executed directly so a missing +x
            # bit (e.g. a fresh checkout) doesn't turn an optional step into
            # a hard failure; `|| true` keeps a failure inside it from
            # aborting setup after everything else already succeeded.
            bash "${SCRIPT_DIR}/optimize-rpi5.sh" || echo -e "${YELLOW}optimize-rpi5.sh exited with an error; continuing.${NC}"
        else
            echo -e "${YELLOW}${SCRIPT_DIR}/optimize-rpi5.sh not found; skipping system-level tuning.${NC}"
        fi
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
echo -e "1. Review .env: ${MINECRAFT_DIR}/.env"
echo -e "2. Navigate to the directory: cd ${MINECRAFT_DIR}"
echo -e "3. Start the server: docker compose up -d"
echo -e "4. View logs: docker compose logs -f"
echo -e "5. Stop the server: docker compose down"
echo -e ""
echo -e "${YELLOW}Note: You may need to log out and back in for Docker permissions to take effect${NC}"
echo -e "${BLUE}========================================${NC}"
