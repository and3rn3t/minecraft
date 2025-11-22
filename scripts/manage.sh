#!/bin/bash
# Minecraft Server Management Script

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to display usage
usage() {
    echo -e "${BLUE}Minecraft Server Management Script${NC}"
    echo -e ""
    echo -e "Usage: $0 {start|stop|restart|status|logs|backup|console|update}"
    echo -e ""
    echo -e "Commands:"
    echo -e "  start    - Start the Minecraft server"
    echo -e "  stop     - Stop the Minecraft server"
    echo -e "  restart  - Restart the Minecraft server"
    echo -e "  status   - Check server status"
    echo -e "  logs     - View server logs"
    echo -e "  backup   - Create a backup of the server"
    echo -e "  console  - Attach to server console"
    echo -e "  update   - Update server configuration"
    exit 1
}

# Function to start server
start_server() {
    echo -e "${GREEN}Starting Minecraft server...${NC}"
    docker-compose up -d
    echo -e "${GREEN}Server started! Use '$0 logs' to view logs${NC}"
}

# Function to stop server
stop_server() {
    echo -e "${YELLOW}Stopping Minecraft server...${NC}"
    docker-compose down
    echo -e "${GREEN}Server stopped${NC}"
}

# Function to restart server
restart_server() {
    echo -e "${YELLOW}Restarting Minecraft server...${NC}"
    docker-compose restart
    echo -e "${GREEN}Server restarted${NC}"
}

# Function to check status
check_status() {
    echo -e "${BLUE}Checking server status...${NC}"
    docker-compose ps
}

# Function to view logs
view_logs() {
    echo -e "${BLUE}Viewing server logs (Press Ctrl+C to exit)...${NC}"
    docker-compose logs -f
}

# Function to create backup
create_backup() {
    echo -e "${YELLOW}Creating backup...${NC}"
    BACKUP_DIR="./backups"
    mkdir -p "$BACKUP_DIR"
    
    TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
    BACKUP_FILE="$BACKUP_DIR/minecraft_backup_$TIMESTAMP.tar.gz"
    
    if [ -d "./data" ]; then
        tar -czf "$BACKUP_FILE" -C ./data .
        echo -e "${GREEN}Backup created: $BACKUP_FILE${NC}"
    else
        echo -e "${RED}No data directory found${NC}"
        exit 1
    fi
}

# Function to attach to console
attach_console() {
    echo -e "${BLUE}Attaching to server console (Press Ctrl+P then Ctrl+Q to detach)...${NC}"
    docker attach minecraft-server
}

# Function to update configuration
update_config() {
    echo -e "${YELLOW}Pulling latest configuration...${NC}"
    git pull
    echo -e "${GREEN}Configuration updated. Run '$0 restart' to apply changes${NC}"
}

# Main script logic
case "${1}" in
    start)
        start_server
        ;;
    stop)
        stop_server
        ;;
    restart)
        restart_server
        ;;
    status)
        check_status
        ;;
    logs)
        view_logs
        ;;
    backup)
        create_backup
        ;;
    console)
        attach_console
        ;;
    update)
        update_config
        ;;
    *)
        usage
        ;;
esac
