#!/bin/bash
# Setup script for API server virtual environment
# Creates and configures a Python virtual environment for the API server

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
API_DIR="${PROJECT_DIR}/api"
VENV_DIR="${API_DIR}/venv"

echo -e "${BLUE}=== API Server Virtual Environment Setup ===${NC}\n"

# Check if Python 3 is available
if ! command -v python3 >/dev/null 2>&1; then
    echo -e "${RED}Error: Python 3 not found${NC}"
    echo -e "${YELLOW}Install Python 3: sudo apt install python3 python3-venv${NC}"
    exit 1
fi

# Check Python version
PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
echo -e "${BLUE}Python version: $(python3 --version)${NC}"

# Navigate to API directory
cd "$API_DIR" || exit 1

# Check if venv already exists
if [ -d "$VENV_DIR" ]; then
    echo -e "${YELLOW}Virtual environment already exists at: $VENV_DIR${NC}"
    read -p "Recreate virtual environment? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${BLUE}Removing existing virtual environment...${NC}"
        rm -rf "$VENV_DIR"
    else
        echo -e "${BLUE}Using existing virtual environment${NC}"
        SKIP_CREATE=true
    fi
else
    SKIP_CREATE=false
fi

# Create virtual environment
if [ "$SKIP_CREATE" != true ]; then
    echo -e "${BLUE}Creating virtual environment...${NC}"
    python3 -m venv "$VENV_DIR"

    if [ ! -d "$VENV_DIR" ]; then
        echo -e "${RED}Failed to create virtual environment${NC}"
        exit 1
    fi

    echo -e "${GREEN}✓ Virtual environment created${NC}"
fi

# Activate virtual environment
echo -e "${BLUE}Activating virtual environment...${NC}"
source "$VENV_DIR/bin/activate"

# Upgrade pip
echo -e "${BLUE}Upgrading pip...${NC}"
pip install --upgrade pip

# Install dependencies
if [ -f "requirements.txt" ]; then
    echo -e "${BLUE}Installing dependencies from requirements.txt...${NC}"
    pip install -r requirements.txt

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Dependencies installed successfully${NC}"
    else
        echo -e "${RED}✗ Failed to install some dependencies${NC}"
        echo -e "${YELLOW}Check requirements.txt and try again${NC}"
        exit 1
    fi
else
    echo -e "${YELLOW}⚠ requirements.txt not found${NC}"
fi

# Verify installation
echo -e "\n${BLUE}Verifying installation...${NC}"
if python -c "import flask" 2>/dev/null; then
    echo -e "${GREEN}✓ Flask is installed${NC}"
else
    echo -e "${RED}✗ Flask not found - installation may have failed${NC}"
    exit 1
fi

# Show installed packages
echo -e "\n${BLUE}Installed packages:${NC}"
pip list | head -10

# Deactivate (we're done)
deactivate

echo -e "\n${GREEN}=== Setup Complete ===${NC}"
echo -e "${BLUE}Virtual environment location: ${VENV_DIR}${NC}"
echo -e "${BLUE}Python executable: ${VENV_DIR}/bin/python${NC}"
echo -e "\n${YELLOW}To activate manually:${NC}"
echo -e "  source ${VENV_DIR}/bin/activate"
echo -e "\n${YELLOW}The systemd service will use this venv automatically.${NC}"

