#!/bin/bash
# Script to update codebase from GitHub and update all components

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

echo -e "${BLUE}=== Codebase Update Script ===${NC}\n"

# Check if we're in a git repository
if [ ! -d "$PROJECT_DIR/.git" ]; then
    echo -e "${RED}Error: Not a git repository${NC}"
    echo -e "${YELLOW}Make sure you cloned the repository with 'git clone'${NC}"
    exit 1
fi

cd "$PROJECT_DIR" || exit 1

# Check current status
echo -e "${BLUE}Checking git status...${NC}"
CURRENT_BRANCH=$(git branch --show-current)
CURRENT_COMMIT=$(git log -1 --oneline)

echo -e "Current branch: ${CURRENT_BRANCH}"
echo -e "Current commit: ${CURRENT_COMMIT}"

# Check for uncommitted changes
if ! git diff-index --quiet HEAD --; then
    echo -e "${YELLOW}⚠ Uncommitted changes detected${NC}"
    read -p "Stash changes before pulling? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        git stash push -m "Stashed before update $(date)"
        echo -e "${GREEN}✓ Changes stashed${NC}"
        STASHED=true
    else
        echo -e "${YELLOW}Proceeding with uncommitted changes...${NC}"
        STASHED=false
    fi
else
    STASHED=false
fi

# Pull latest changes
echo -e "\n${BLUE}Pulling latest changes from GitHub...${NC}"
if git pull origin "$CURRENT_BRANCH"; then
    echo -e "${GREEN}✓ Code updated successfully${NC}"
else
    echo -e "${RED}✗ Failed to pull changes${NC}"
    if [ "$STASHED" = true ]; then
        echo -e "${YELLOW}Restoring stashed changes...${NC}"
        git stash pop || true
    fi
    exit 1
fi

# Show what changed
echo -e "\n${BLUE}Recent changes:${NC}"
git log --oneline -5

# Check what files changed
CHANGED_FILES=$(git diff --name-only HEAD~1 HEAD 2>/dev/null || echo "")
WEB_CHANGED=false
API_CHANGED=false
DOCKER_CHANGED=false
SYSTEMD_CHANGED=false

if echo "$CHANGED_FILES" | grep -q "^web/"; then
    WEB_CHANGED=true
fi

if echo "$CHANGED_FILES" | grep -q "^api/"; then
    API_CHANGED=true
fi

if echo "$CHANGED_FILES" | grep -q "Dockerfile\|docker-compose"; then
    DOCKER_CHANGED=true
fi

if echo "$CHANGED_FILES" | grep -q "^systemd/"; then
    SYSTEMD_CHANGED=true
fi

# Update web interface if changed
if [ "$WEB_CHANGED" = true ] || [ "$1" = "--all" ]; then
    echo -e "\n${BLUE}Updating web interface...${NC}"
    if [ -d "$PROJECT_DIR/web" ]; then
        cd "$PROJECT_DIR/web" || exit 1

        if [ -f "package.json" ]; then
            echo -e "${BLUE}Installing npm dependencies...${NC}"
            npm install

            echo -e "${BLUE}Building web interface...${NC}"
            npm run build

            echo -e "${GREEN}✓ Web interface updated${NC}"

            # Reload nginx if service exists
            if systemctl is-active --quiet nginx 2>/dev/null; then
                echo -e "${BLUE}Reloading nginx...${NC}"
                sudo systemctl reload nginx || true
            fi
        else
            echo -e "${YELLOW}⚠ package.json not found, skipping web update${NC}"
        fi
    else
        echo -e "${YELLOW}⚠ web/ directory not found${NC}"
    fi
fi

# Update API server if changed
if [ "$API_CHANGED" = true ] || [ "$1" = "--all" ]; then
    echo -e "\n${BLUE}Updating API server...${NC}"
    if [ -d "$PROJECT_DIR/api" ]; then
        # Use venv setup script if available
        if [ -f "$PROJECT_DIR/scripts/setup-api-venv.sh" ]; then
            echo -e "${BLUE}Updating virtual environment and dependencies...${NC}"
            "$PROJECT_DIR/scripts/setup-api-venv.sh" || {
                echo -e "${YELLOW}⚠ Venv setup failed, trying manual update...${NC}"
                cd "$PROJECT_DIR/api" || exit 1
                if [ -d "venv" ]; then
                    source venv/bin/activate
                    pip install -r requirements.txt
                    deactivate
                else
                    echo -e "${YELLOW}⚠ Virtual environment not found, creating...${NC}"
                    "$PROJECT_DIR/scripts/setup-api-venv.sh"
                fi
            }
        else
            # Fallback: manual venv update
            cd "$PROJECT_DIR/api" || exit 1
            if [ -d "venv" ] && [ -f "requirements.txt" ]; then
                echo -e "${BLUE}Updating dependencies in virtual environment...${NC}"
                source venv/bin/activate
                pip install -r requirements.txt
                deactivate
            elif [ -f "requirements.txt" ]; then
                echo -e "${YELLOW}⚠ Virtual environment not found, creating...${NC}"
                python3 -m venv venv
                source venv/bin/activate
                pip install -r requirements.txt
                deactivate
            else
                echo -e "${YELLOW}⚠ requirements.txt not found, skipping API update${NC}"
            fi
        fi

        echo -e "${GREEN}✓ API dependencies updated${NC}"

        # Restart API service if exists
        if systemctl is-active --quiet minecraft-api.service 2>/dev/null; then
            echo -e "${BLUE}Restarting API service...${NC}"
            sudo systemctl restart minecraft-api.service || true
        fi
    else
        echo -e "${YELLOW}⚠ api/ directory not found${NC}"
    fi
fi

# Update Docker if changed
if [ "$DOCKER_CHANGED" = true ] || [ "$1" = "--all" ]; then
    echo -e "\n${BLUE}Updating Docker configuration...${NC}"
    cd "$PROJECT_DIR" || exit 1

    # Check if using registry-based compose
    if grep -q "image:" docker-compose.yml 2>/dev/null && ! grep -q "build:" docker-compose.yml 2>/dev/null; then
        echo -e "${BLUE}Pulling latest Docker image...${NC}"
        docker compose pull || echo -e "${YELLOW}⚠ Failed to pull image (may need authentication)${NC}"
    fi

    echo -e "${BLUE}Recreating containers...${NC}"
    docker compose up -d --force-recreate || echo -e "${YELLOW}⚠ Failed to recreate containers${NC}"

    echo -e "${GREEN}✓ Docker updated${NC}"
fi

# Update systemd services if changed
if [ "$SYSTEMD_CHANGED" = true ] || [ "$1" = "--all" ]; then
    echo -e "\n${BLUE}Updating systemd services...${NC}"
    if [ -d "$PROJECT_DIR/systemd" ]; then
        cd "$PROJECT_DIR" || exit 1

        # Copy service files
        for service_file in systemd/*.service; do
            if [ -f "$service_file" ]; then
                echo -e "${BLUE}Installing $(basename "$service_file")...${NC}"
                sudo cp "$service_file" /etc/systemd/system/ || true
            fi
        done

        # Reload systemd
        sudo systemctl daemon-reload || true
        echo -e "${GREEN}✓ Systemd services updated${NC}"
    fi
fi

# Restore stashed changes if any
if [ "$STASHED" = true ]; then
    echo -e "\n${BLUE}Restoring stashed changes...${NC}"
    if git stash list | grep -q "Stashed before update"; then
        git stash pop || echo -e "${YELLOW}⚠ Could not restore stashed changes${NC}"
    fi
fi

# Summary
echo -e "\n${BLUE}=== Update Summary ===${NC}"
echo -e "Branch: ${CURRENT_BRANCH}"
echo -e "New commit: $(git log -1 --oneline)"

if [ "$WEB_CHANGED" = true ]; then
    echo -e "${GREEN}✓ Web interface updated${NC}"
fi

if [ "$API_CHANGED" = true ]; then
    echo -e "${GREEN}✓ API server updated${NC}"
fi

if [ "$DOCKER_CHANGED" = true ]; then
    echo -e "${GREEN}✓ Docker updated${NC}"
fi

if [ "$SYSTEMD_CHANGED" = true ]; then
    echo -e "${GREEN}✓ Systemd services updated${NC}"
fi

if [ "$WEB_CHANGED" = false ] && [ "$API_CHANGED" = false ] && [ "$DOCKER_CHANGED" = false ] && [ "$SYSTEMD_CHANGED" = false ] && [ "$1" != "--all" ]; then
    echo -e "${YELLOW}No component-specific changes detected${NC}"
    echo -e "${YELLOW}Run with --all flag to update all components: ./scripts/update-codebase.sh --all${NC}"
fi

echo -e "\n${GREEN}✓ Update complete!${NC}"

# Run health check if available
if [ -f "$PROJECT_DIR/scripts/check-services.sh" ]; then
    echo -e "\n${BLUE}Running health check...${NC}"
    "$PROJECT_DIR/scripts/check-services.sh" || true
fi

