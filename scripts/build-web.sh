#!/bin/bash
# Build script for web interface
# Builds the React app for production deployment

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
WEB_DIR="${PROJECT_DIR}/web"

echo -e "${BLUE}Building web interface for production...${NC}"

# Check if Node.js is installed
if ! command -v node >/dev/null 2>&1; then
    echo -e "${RED}Error: Node.js is not installed${NC}"
    echo -e "${YELLOW}Install Node.js 18+ to build the web interface${NC}"
    exit 1
fi

# Check Node.js version
NODE_VERSION=$(node -v | cut -d'v' -f2 | cut -d'.' -f1)
if [ "$NODE_VERSION" -lt 18 ]; then
    echo -e "${RED}Error: Node.js version 18+ is required (found: $(node -v))${NC}"
    exit 1
fi

# Navigate to web directory
cd "$WEB_DIR" || exit 1

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    echo -e "${BLUE}Installing dependencies...${NC}"
    npm install
fi

# Build the project
echo -e "${BLUE}Building React app...${NC}"
npm run build

if [ -d "dist" ] && [ -f "dist/index.html" ]; then
    echo -e "${GREEN}✓ Web interface built successfully!${NC}"
    echo -e "${BLUE}Build output: ${WEB_DIR}/dist${NC}"
    echo -e "${YELLOW}Make sure nginx is configured to serve from this directory${NC}"
else
    echo -e "${RED}✗ Build failed - dist directory not found${NC}"
    exit 1
fi

