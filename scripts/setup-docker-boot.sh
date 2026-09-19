#!/bin/bash
# Docker Boot Setup Script for Raspberry Pi 5
# Configures systemd to automatically pull and start Docker containers on boot
#
# Usage:
#   ./setup-docker-boot.sh docker-compose    # For docker-compose setup
#   ./setup-docker-boot.sh docker-run        # For docker run setup
#   ./setup-docker-boot.sh minecraft         # For Minecraft server setup

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# Service name
SERVICE_NAME="${SERVICE_NAME:-docker-app}"

# Function to print header
print_header() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
}

# Function to check if running as root
check_root() {
    if [ "$EUID" -eq 0 ]; then
        echo -e "${RED}Error: Do not run this script as root${NC}"
        echo -e "${YELLOW}Run as your regular user (pi or your username)${NC}"
        exit 1
    fi
}

# Function to check if Docker is installed
check_docker() {
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}Error: Docker is not installed${NC}"
        echo -e "${YELLOW}Please install Docker first:${NC}"
        echo -e "  curl -fsSL https://get.docker.com -o get-docker.sh"
        echo -e "  sudo sh get-docker.sh"
        exit 1
    fi

    if ! groups | grep -q docker; then
        echo -e "${YELLOW}Warning: User not in docker group${NC}"
        echo -e "${YELLOW}Adding user to docker group...${NC}"
        sudo usermod -aG docker "$USER"
        echo -e "${GREEN}User added to docker group${NC}"
        echo -e "${YELLOW}Please log out and back in for changes to take effect${NC}"
        echo -e "${YELLOW}Then run this script again${NC}"
        exit 0
    fi
}

# Function to detect docker compose command
detect_docker_compose() {
    # Check for docker compose plugin first (modern approach)
    if docker compose version &> /dev/null; then
        echo "docker compose"
        return 0
    fi
    # Fall back to standalone docker-compose
    if command -v docker-compose &> /dev/null; then
        echo "docker-compose"
        return 0
    fi
    # Not found
    return 1
}

# Function to setup docker-compose service
setup_docker_compose() {
    local work_dir="${1:-$HOME/docker-app}"
    local compose_file="${2:-docker-compose.yml}"

    print_header "Setting up Docker Compose Auto-Start"

    # Detect docker compose command
    local compose_cmd
    if ! compose_cmd=$(detect_docker_compose); then
        echo -e "${YELLOW}Docker Compose not found${NC}"
        echo -e "${YELLOW}Attempting to install...${NC}"
        sudo apt-get update
        if sudo apt-get install -y docker-compose-plugin 2>/dev/null; then
            compose_cmd="docker compose"
        elif sudo apt-get install -y docker-compose 2>/dev/null; then
            compose_cmd="docker-compose"
        else
            echo -e "${RED}Error: Could not install Docker Compose${NC}"
            echo -e "${YELLOW}Please install manually:${NC}"
            echo -e "  sudo apt-get install -y docker-compose-plugin"
            exit 1
        fi
    else
        echo -e "${GREEN}Found Docker Compose: $compose_cmd${NC}"
    fi

    # Check if docker-compose.yml exists
    if [ ! -f "$work_dir/$compose_file" ]; then
        echo -e "${YELLOW}Warning: $compose_file not found in $work_dir${NC}"
        read -p "Create directory and continue? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
        mkdir -p "$work_dir"
    fi

    # Get absolute path
    work_dir="$(cd "$work_dir" && pwd)"

    # Determine how to execute docker compose command
    # Systemd doesn't handle spaces well, so we need to wrap in shell for plugin version
    local exec_start_pre
    local exec_start
    local exec_stop
    local exec_reload

    if [ "$compose_cmd" = "docker compose" ]; then
        # Use shell wrapper for docker compose plugin (has space)
        exec_start_pre="/bin/sh -c 'cd ${work_dir} && /usr/bin/docker compose pull'"
        exec_start="/bin/sh -c 'cd ${work_dir} && /usr/bin/docker compose up -d'"
        exec_stop="/bin/sh -c 'cd ${work_dir} && /usr/bin/docker compose down'"
        exec_reload="/bin/sh -c 'cd ${work_dir} && /usr/bin/docker compose up -d --force-recreate'"
    else
        # Standalone docker-compose (no space, direct path)
        exec_start_pre="/usr/bin/docker-compose -f ${work_dir}/docker-compose.yml pull"
        exec_start="/usr/bin/docker-compose -f ${work_dir}/docker-compose.yml up -d"
        exec_stop="/usr/bin/docker-compose -f ${work_dir}/docker-compose.yml down"
        exec_reload="/usr/bin/docker-compose -f ${work_dir}/docker-compose.yml up -d --force-recreate"
    fi

    # Create systemd service file
    echo -e "${GREEN}Creating systemd service...${NC}"
    sudo tee "/etc/systemd/system/${SERVICE_NAME}.service" > /dev/null << EOF
[Unit]
Description=Docker Application Service
After=docker.service network-online.target
Requires=docker.service
Wants=network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=${work_dir}
ExecStartPre=${exec_start_pre}
ExecStart=${exec_start}
ExecStop=${exec_stop}
ExecReload=${exec_reload}
Restart=on-failure
RestartSec=10
User=${USER}
Group=${USER}

[Install]
WantedBy=multi-user.target
EOF

    echo -e "${GREEN}Service file created${NC}"
}

# Function to setup docker run service
setup_docker_run() {
    print_header "Setting up Docker Run Auto-Start"

    # Prompt for image name
    read -p "Enter Docker image name (e.g., nginx:latest): " image_name
    if [ -z "$image_name" ]; then
        echo -e "${RED}Error: Image name is required${NC}"
        exit 1
    fi

    # Prompt for container name
    read -p "Enter container name [docker-app]: " container_name
    container_name="${container_name:-docker-app}"

    # Prompt for ports
    read -p "Enter port mappings (e.g., 8080:80) [press Enter to skip]: " port_mappings
    port_args=""
    if [ -n "$port_mappings" ]; then
        port_args="-p $port_mappings"
    fi

    # Prompt for volumes
    read -p "Enter volume mappings (e.g., /data:/app/data) [press Enter to skip]: " volume_mappings
    volume_args=""
    if [ -n "$volume_mappings" ]; then
        volume_args="-v $volume_mappings"
    fi

    # Prompt for environment variables
    read -p "Enter environment variables (e.g., KEY=value) [press Enter to skip]: " env_vars
    env_args=""
    if [ -n "$env_vars" ]; then
        env_args="-e $env_vars"
    fi

    # Create systemd service file
    echo -e "${GREEN}Creating systemd service...${NC}"
    sudo tee "/etc/systemd/system/${SERVICE_NAME}.service" > /dev/null << EOF
[Unit]
Description=Docker Application Container
After=docker.service network-online.target
Requires=docker.service
Wants=network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStartPre=-/usr/bin/docker stop ${container_name}
ExecStartPre=-/usr/bin/docker rm ${container_name}
ExecStartPre=/usr/bin/docker pull ${image_name}
ExecStart=/usr/bin/docker run --name ${container_name} \\
    --restart unless-stopped \\
    ${port_args} \\
    ${volume_args} \\
    ${env_args} \\
    ${image_name}
ExecStop=/usr/bin/docker stop ${container_name}
ExecStopPost=/usr/bin/docker rm ${container_name}
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

    echo -e "${GREEN}Service file created${NC}"
}

# Function to setup Minecraft server service
setup_minecraft() {
    print_header "Setting up Minecraft Server Auto-Start"

    local work_dir="$PROJECT_DIR"
    local compose_file="docker-compose.yml"

    # Check if we're in the right directory
    if [ ! -f "$work_dir/$compose_file" ]; then
        echo -e "${RED}Error: docker-compose.yml not found${NC}"
        echo -e "${YELLOW}Please run this script from the minecraft-server directory${NC}"
        exit 1
    fi

    SERVICE_NAME="minecraft"

    # Ensure docker compose is available
    if ! detect_docker_compose &> /dev/null; then
        echo -e "${YELLOW}Docker Compose not found, checking installation...${NC}"
        # The setup_docker_compose function will handle installation
    fi

    setup_docker_compose "$work_dir" "$compose_file"
}

# Function to enable and start service
enable_service() {
    print_header "Enabling Service"

    echo -e "${GREEN}Reloading systemd daemon...${NC}"
    sudo systemctl daemon-reload

    echo -e "${GREEN}Enabling ${SERVICE_NAME}.service...${NC}"
    sudo systemctl enable "${SERVICE_NAME}.service"

    echo -e "${GREEN}Starting ${SERVICE_NAME}.service...${NC}"
    sudo systemctl start "${SERVICE_NAME}.service"

    echo -e "${GREEN}Service enabled and started${NC}"
}

# Function to show service status
show_status() {
    print_header "Service Status"

    echo -e "${BLUE}Systemd Service:${NC}"
    sudo systemctl status "${SERVICE_NAME}.service" --no-pager -l || true

    echo -e "\n${BLUE}Docker Containers:${NC}"
    docker ps || true

    echo -e "\n${BLUE}Service Logs (last 20 lines):${NC}"
    sudo journalctl -u "${SERVICE_NAME}.service" -n 20 --no-pager || true
}

# Function to show usage
usage() {
    cat << EOF
Usage: $0 [OPTION] [MODE]

Modes:
  docker-compose [WORK_DIR] [COMPOSE_FILE]  Setup for docker-compose
  docker-run                                 Setup for docker run
  minecraft                                  Setup for Minecraft server

Options:
  -n, --name NAME                            Service name (default: docker-app)
  -s, --status                               Show service status
  -h, --help                                 Show this help message

Examples:
  $0 docker-compose ~/my-app docker-compose.yml
  $0 docker-run
  $0 minecraft
  $0 --status

EOF
}

# Main execution
main() {
    local mode=""
    local work_dir=""
    local compose_file=""

    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -n|--name)
                SERVICE_NAME="$2"
                shift 2
                ;;
            -s|--status)
                if [ -z "$SERVICE_NAME" ]; then
                    SERVICE_NAME="docker-app"
                fi
                show_status
                exit 0
                ;;
            -h|--help)
                usage
                exit 0
                ;;
            docker-compose|docker-run|minecraft)
                mode="$1"
                shift
                if [ "$mode" = "docker-compose" ] && [ $# -gt 0 ]; then
                    work_dir="$1"
                    shift
                    if [ $# -gt 0 ]; then
                        compose_file="$1"
                        shift
                    fi
                fi
                ;;
            *)
                echo -e "${RED}Unknown option: $1${NC}"
                usage
                exit 1
                ;;
        esac
    done

    # If no mode specified, show usage
    if [ -z "$mode" ]; then
        usage
        exit 1
    fi

    # Check prerequisites
    check_root
    check_docker

    # Setup based on mode
    case "$mode" in
        docker-compose)
            setup_docker_compose "${work_dir:-$HOME/docker-app}" "${compose_file:-docker-compose.yml}"
            ;;
        docker-run)
            setup_docker_run
            ;;
        minecraft)
            setup_minecraft
            ;;
        *)
            echo -e "${RED}Unknown mode: $mode${NC}"
            usage
            exit 1
            ;;
    esac

    # Enable service
    enable_service

    # Show status
    echo ""
    show_status

    # Final instructions
    echo ""
    print_header "Setup Complete"
    echo -e "${GREEN}Service ${SERVICE_NAME}.service has been configured and started${NC}"
    echo ""
    echo -e "${YELLOW}Useful commands:${NC}"
    echo -e "  Check status:  sudo systemctl status ${SERVICE_NAME}.service"
    echo -e "  View logs:     sudo journalctl -u ${SERVICE_NAME}.service -f"
    echo -e "  Stop service:  sudo systemctl stop ${SERVICE_NAME}.service"
    echo -e "  Start service: sudo systemctl start ${SERVICE_NAME}.service"
    echo -e "  Restart:       sudo systemctl restart ${SERVICE_NAME}.service"
    echo -e "  Disable:       sudo systemctl disable ${SERVICE_NAME}.service"
    echo ""
    echo -e "${YELLOW}The service will automatically start on boot${NC}"
    echo -e "${YELLOW}Test by rebooting: sudo reboot${NC}"
}

# Run main function
main "$@"

