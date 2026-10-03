#!/bin/bash
# System Cleanup Script
# Cleans up disk space, old files, and temporary data

set -e

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source-path=SCRIPTDIR
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo -e "${BLUE}=== System Cleanup ===${NC}\n"

# Track space freed
SPACE_FREED=0

# 1. Clean Docker
echo -e "${BLUE}[1/7] Cleaning Docker...${NC}"
BEFORE=$(df -h / | awk 'NR==2 {print $4}')
# Dangling images and week-old build cache are what a Pi that builds its own
# image piles up. This is deliberately not `docker system prune -af --volumes`:
# that removes every image no running container uses (a stopped server's image
# would have to be rebuilt) and every unused volume, whatever put it there.
DOCKER_OK=true
if ! docker image prune -f > /dev/null 2>&1; then
    DOCKER_OK=false
    echo -e "${YELLOW}⚠ Could not prune Docker images${NC}"
fi
if ! docker builder prune -f --filter "until=168h" > /dev/null 2>&1; then
    DOCKER_OK=false
    echo -e "${YELLOW}⚠ Could not prune the Docker build cache${NC}"
fi
AFTER=$(df -h / | awk 'NR==2 {print $4}')
if [ "$DOCKER_OK" = true ]; then
    echo -e "${GREEN}✓ Docker cleaned (free space ${BEFORE} -> ${AFTER})${NC}"
else
    echo -e "${YELLOW}⚠ Docker cleaned with warnings (free space ${BEFORE} -> ${AFTER})${NC}"
fi

# 2. Backups are not touched here. scripts/backup-scheduler.sh runs
# scripts/cleanup-backups.sh after every backup, which prunes by the retention
# policy in config/backup-retention.conf. A blanket "older than 30 days" delete
# ignored that policy, could leave fewer backups than it promised to keep, and
# also took the safety backups made when a world is deleted.
echo -e "\n${BLUE}[2/7] Backups...${NC}"
echo -e "${YELLOW}⚠ Left alone: pruned by the retention policy (scripts/cleanup-backups.sh)${NC}"

# 3. Clean old logs
echo -e "\n${BLUE}[3/7] Cleaning old logs...${NC}"
if [ -d "$PROJECT_DIR/data/logs" ]; then
    find "$PROJECT_DIR/data/logs" -name "*.log.gz" -type f -mtime +14 -delete
    echo -e "${GREEN}✓ Old compressed logs cleaned${NC}"
fi

if [ -d "$PROJECT_DIR/logs" ]; then
    find "$PROJECT_DIR/logs" -name "*.log" -type f -mtime +30 -delete
    echo -e "${GREEN}✓ Old application logs cleaned${NC}"
fi

# 4. Clean package cache
echo -e "\n${BLUE}[4/7] Cleaning package cache...${NC}"
sudo apt-get clean -qq
sudo apt-get autoremove -y -qq
echo -e "${GREEN}✓ Package cache cleaned${NC}"

# 5. Clean tool caches. Not /tmp or the whole of ~/.cache: other programs keep
# live files there (sockets, lock files, a running build's scratch space).
echo -e "\n${BLUE}[5/7] Cleaning tool caches...${NC}"
rm -rf "${HOME}/.cache/pip" 2>/dev/null || true
echo -e "${GREEN}✓ pip cache cleaned${NC}"

# 6. Clean Python cache
echo -e "\n${BLUE}[6/7] Cleaning Python cache...${NC}"
find "$PROJECT_DIR" -type d -name "__pycache__" -exec rm -r {} + 2>/dev/null || true
find "$PROJECT_DIR" -type f -name "*.pyc" -delete 2>/dev/null || true
find "$PROJECT_DIR" -type f -name "*.pyo" -delete 2>/dev/null || true
echo -e "${GREEN}✓ Python cache cleaned${NC}"

# 7. Clean Node.js cache (if web directory exists)
echo -e "\n${BLUE}[7/7] Cleaning Node.js cache...${NC}"
if [ -d "$PROJECT_DIR/web" ]; then
    cd "$PROJECT_DIR/web" || exit 1
    if [ -d "node_modules/.cache" ]; then
        rm -rf node_modules/.cache
        echo -e "${GREEN}✓ Node.js cache cleaned${NC}"
    fi
fi

# Report disk usage
echo -e "\n${BLUE}=== Disk Usage Report ===${NC}"
df -h / | tail -1

echo -e "\n${BLUE}Project directory sizes:${NC}"
du -sh "$PROJECT_DIR"/* 2>/dev/null | sort -h | tail -10

echo -e "\n${GREEN}✓ Cleanup complete!${NC}"
