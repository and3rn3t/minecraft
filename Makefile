# Minecraft Server Management Makefile
# Provides convenient commands for server management

.PHONY: help start stop restart status logs backup console update install clean test

# Default target
help:
	@echo "Minecraft Server Management Commands:"
	@echo ""
	@echo "  make install     - Install dependencies and setup"
	@echo "  make start       - Start the server"
	@echo "  make stop        - Stop the server"
	@echo "  make restart     - Restart the server"
	@echo "  make status      - Check server status"
	@echo "  make logs        - View server logs"
	@echo "  make backup      - Create a backup"
	@echo "  make console     - Attach to server console"
	@echo "  make update      - Update server configuration"
	@echo "  make clean       - Clean up Docker resources"
	@echo "  make test        - Run tests"
	@echo "  make build       - Build Docker image"
	@echo "  make shell       - Open shell in container"
	@echo ""

# Installation
install:
	@echo "Installing dependencies..."
	@chmod +x setup-rpi.sh manage.sh start.sh
	@./setup-rpi.sh

# Server management
start:
	@./manage.sh start

stop:
	@./manage.sh stop

restart:
	@./manage.sh restart

status:
	@./manage.sh status

logs:
	@./manage.sh logs

backup:
	@./manage.sh backup

console:
	@./manage.sh console

update:
	@./manage.sh update

# Docker operations
build:
	@echo "Building Docker image..."
	@docker-compose build

clean:
	@echo "Cleaning up Docker resources..."
	@docker-compose down -v
	@docker system prune -f

shell:
	@docker exec -it minecraft-server /bin/bash

# Testing
test:
	@echo "Running tests..."
	@bash -n manage.sh
	@bash -n start.sh
	@bash -n setup-rpi.sh
	@docker-compose config > /dev/null
	@echo "All tests passed!"

# Development
dev-start:
	@echo "Starting in development mode..."
	@docker-compose up

dev-stop:
	@echo "Stopping development mode..."
	@docker-compose down

# Backup management
backup-list:
	@ls -lh backups/ | tail -n +2

backup-clean:
	@echo "Cleaning old backups (keeping last 7 days)..."
	@find backups -name "minecraft_backup_*.tar.gz" -mtime +7 -delete
	@echo "Backup cleanup complete"

# System information
info:
	@echo "=== Server Information ==="
	@echo "Docker version:"
	@docker --version
	@echo ""
	@echo "Docker Compose version:"
	@docker-compose --version
	@echo ""
	@echo "System resources:"
	@free -h
	@echo ""
	@echo "Disk usage:"
	@df -h
	@echo ""
	@echo "Server status:"
	@./manage.sh status

# Quick setup
quick-setup: install
	@echo "Quick setup complete!"
	@echo "Next steps:"
	@echo "  1. Copy .env.example to .env and configure"
	@echo "  2. Run 'make start' to start the server"
	@echo "  3. Run 'make logs' to view server logs"

