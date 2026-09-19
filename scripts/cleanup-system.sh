#!/bin/bash
# System Cleanup Script
# Cleans up disk space, old files, and temporary data

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

echo -e "${BLUE}=== System Cleanup ===${NC}\n"

# Track space freed
SPACE_FREED=0

# 1. Clean Docker
echo -e "${BLUE}[1/7] Cleaning Docker...${NC}"
BEFORE=$(df -h / | awk 'NR==2 {print $4}')
docker system prune -af --volumes --filter "until=168h" 2>/dev/null || true
AFTER=$(df -h / | awk 'NR==2 {print $4}')
echo -e "${GREEN}✓ Docker cleaned${NC}"

# 2. Clean old backups (keep last 10)
echo -e "\n${BLUE}[2/7] Cleaning old backups...${NC}"
if [ -d "$PROJECT_DIR/backups" ]; then
    BACKUP_COUNT=$(find "$PROJECT_DIR/backups" -name "*.tar.gz" -type f | wc -l)
    if [ "$BACKUP_COUNT" -gt 10 ]; then
        # Delete backups older than 30 days, but keep at least 10
        find "$PROJECT_DIR/backups" -name "*.tar.gz" -type f -mtime +30 -delete
        echo -e "${GREEN}✓ Old backups cleaned (kept last 10)${NC}"
    else
        echo -e "${YELLOW}⚠ Only $BACKUP_COUNT backups found, keeping all${NC}"
    fi
else
    echo -e "${YELLOW}⚠ Backups directory not found${NC}"
fi

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

# 5. Clean temporary files
echo -e "\n${BLUE}[5/7] Cleaning temporary files...${NC}"
rm -rf /tmp/* 2>/dev/null || true
rm -rf ~/.cache/* 2>/dev/null || true
echo -e "${GREEN}✓ Temporary files cleaned${NC}"

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

