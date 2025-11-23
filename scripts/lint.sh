#!/bin/bash
# Linting Script
# Runs static code analysis for bash scripts, Python, and JavaScript/React

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

# Lint results
TOTAL_ISSUES=0
FAILED_CHECKS=0

# Function to print header
print_header() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to lint bash scripts with shellcheck
lint_bash() {
    print_header "Linting Bash Scripts with ShellCheck"

    if ! command_exists shellcheck; then
        echo -e "${YELLOW}ShellCheck not found. Installing...${NC}"
        if command_exists apt-get; then
            sudo apt-get update && sudo apt-get install -y shellcheck
        elif command_exists brew; then
            brew install shellcheck
        else
            echo -e "${RED}Please install shellcheck manually: https://github.com/koalaman/shellcheck${NC}"
            FAILED_CHECKS=$((FAILED_CHECKS + 1))
            return 1
        fi
    fi

    local issues=0
    local checked=0

    # Find all bash scripts
    while IFS= read -r -d '' script; do
        checked=$((checked + 1))
        echo -e "${BLUE}Checking: $script${NC}"

        # Run shellcheck
        if ! shellcheck -f gcc "$script" 2>&1 | tee /tmp/shellcheck_output.txt; then
            local script_issues=$(grep -c "error:" /tmp/shellcheck_output.txt 2>/dev/null || echo "0")
            issues=$((issues + script_issues))
        fi
    done < <(find "$PROJECT_DIR" -type f -name "*.sh" -not -path "*/node_modules/*" -not -path "*/.git/*" -print0)

    if [ $issues -eq 0 ]; then
        echo -e "${GREEN}✓ All $checked bash scripts passed shellcheck${NC}"
    else
        echo -e "${RED}✗ Found $issues issues in bash scripts${NC}"
        FAILED_CHECKS=$((FAILED_CHECKS + 1))
        TOTAL_ISSUES=$((TOTAL_ISSUES + issues))
    fi

    echo ""
    return $issues
}

# Function to lint Python code
lint_python() {
    print_header "Linting Python Code"

    if [ ! -d "$PROJECT_DIR/api" ]; then
        echo -e "${YELLOW}Skipping Python linting (api directory not found)${NC}"
        return 0
    fi

    local issues=0

    # Check for flake8
    if command_exists flake8; then
        echo -e "${BLUE}Running flake8...${NC}"
        if ! flake8 "$PROJECT_DIR/api" --max-line-length=100 --ignore=E501,W503,E203 2>&1; then
            issues=$((issues + 1))
        fi
    else
        echo -e "${YELLOW}flake8 not installed. Install with: pip install flake8${NC}"
    fi

    # Check for pylint (optional, more strict)
    if command_exists pylint; then
        echo -e "${BLUE}Running pylint (informational only)...${NC}"
        pylint "$PROJECT_DIR/api" --disable=C0111,R0912,R0913,C0103 || true
    else
        echo -e "${YELLOW}pylint not installed. Install with: pip install pylint${NC}"
    fi

    if [ $issues -eq 0 ]; then
        echo -e "${GREEN}✓ Python code passed linting${NC}"
    else
        echo -e "${RED}✗ Found issues in Python code${NC}"
        FAILED_CHECKS=$((FAILED_CHECKS + 1))
        TOTAL_ISSUES=$((TOTAL_ISSUES + issues))
    fi

    echo ""
    return $issues
}

# Function to lint JavaScript/React code
lint_javascript() {
    print_header "Linting JavaScript/React Code"

    if [ ! -d "$PROJECT_DIR/web" ]; then
        echo -e "${YELLOW}Skipping JavaScript linting (web directory not found)${NC}"
        return 0
    fi

    local issues=0

    # Check if node_modules exists
    if [ ! -d "$PROJECT_DIR/web/node_modules" ]; then
        echo -e "${YELLOW}Installing npm dependencies...${NC}"
        cd "$PROJECT_DIR/web"
        npm install
        cd "$PROJECT_DIR"
    fi

    # Run eslint
    cd "$PROJECT_DIR/web"
    if npm run lint 2>&1; then
        echo -e "${GREEN}✓ JavaScript/React code passed eslint${NC}"
    else
        echo -e "${RED}✗ Found issues in JavaScript/React code${NC}"
        issues=1
        FAILED_CHECKS=$((FAILED_CHECKS + 1))
        TOTAL_ISSUES=$((TOTAL_ISSUES + 1))
    fi
    cd "$PROJECT_DIR"

    echo ""
    return $issues
}

# Function to lint YAML files (docker-compose, etc.)
lint_yaml() {
    print_header "Linting YAML Files"

    if ! command_exists yamllint; then
        echo -e "${YELLOW}yamllint not found. Skipping YAML linting.${NC}"
        echo -e "${YELLOW}Install with: pip install yamllint${NC}"
        return 0
    fi

    local issues=0
    local checked=0

    # Check docker-compose.yml
    if [ -f "$PROJECT_DIR/docker-compose.yml" ]; then
        checked=$((checked + 1))
        echo -e "${BLUE}Checking: docker-compose.yml${NC}"
        if ! yamllint "$PROJECT_DIR/docker-compose.yml" 2>&1; then
            issues=$((issues + 1))
        fi
    fi

    # Check other YAML files
    while IFS= read -r -d '' yaml_file; do
        checked=$((checked + 1))
        echo -e "${BLUE}Checking: $yaml_file${NC}"
        if ! yamllint "$yaml_file" 2>&1; then
            issues=$((issues + 1))
        fi
    done < <(find "$PROJECT_DIR" -type f \( -name "*.yml" -o -name "*.yaml" \) -not -path "*/node_modules/*" -not -path "*/.git/*" -print0)

    if [ $issues -eq 0 ] && [ $checked -gt 0 ]; then
        echo -e "${GREEN}✓ All $checked YAML files passed linting${NC}"
    elif [ $checked -eq 0 ]; then
        echo -e "${YELLOW}No YAML files found to lint${NC}"
    else
        echo -e "${RED}✗ Found issues in YAML files${NC}"
        FAILED_CHECKS=$((FAILED_CHECKS + 1))
        TOTAL_ISSUES=$((TOTAL_ISSUES + issues))
    fi

    echo ""
    return $issues
}

# Function to validate docker-compose.yml
validate_docker_compose() {
    print_header "Validating Docker Compose Configuration"

    if ! command_exists docker-compose && ! docker compose version >/dev/null 2>&1; then
        echo -e "${YELLOW}Docker Compose not found. Skipping validation.${NC}"
        return 0
    fi

    if [ -f "$PROJECT_DIR/docker-compose.yml" ]; then
        echo -e "${BLUE}Validating docker-compose.yml...${NC}"
        if docker-compose config >/dev/null 2>&1 || docker compose config >/dev/null 2>&1; then
            echo -e "${GREEN}✓ docker-compose.yml is valid${NC}"
        else
            echo -e "${RED}✗ docker-compose.yml has errors${NC}"
            FAILED_CHECKS=$((FAILED_CHECKS + 1))
            TOTAL_ISSUES=$((TOTAL_ISSUES + 1))
            return 1
        fi
    else
        echo -e "${YELLOW}docker-compose.yml not found${NC}"
    fi

    echo ""
    return 0
}

# Main function
main() {
    local lint_type="${1:-all}"

    echo -e "${BLUE}"
    echo "╔════════════════════════════════════════╗"
    echo "║   Static Code Analysis - Linting       ║"
    echo "╚════════════════════════════════════════╝"
    echo -e "${NC}"
    echo ""

    case "$lint_type" in
        bash)
            lint_bash
            ;;
        python)
            lint_python
            ;;
        js|javascript)
            lint_javascript
            ;;
        yaml)
            lint_yaml
            ;;
        docker)
            validate_docker_compose
            ;;
        all)
            lint_bash
            lint_python
            lint_javascript
            lint_yaml
            validate_docker_compose
            ;;
        *)
            echo -e "${RED}Unknown lint type: $lint_type${NC}"
            echo "Usage: $0 {all|bash|python|js|yaml|docker}"
            exit 1
            ;;
    esac

    # Summary
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}Linting Summary${NC}"
    echo -e "${BLUE}========================================${NC}"

    if [ $FAILED_CHECKS -eq 0 ] && [ $TOTAL_ISSUES -eq 0 ]; then
        echo -e "${GREEN}✓ All linting checks passed!${NC}"
        echo ""
        exit 0
    else
        echo -e "${RED}✗ Linting found $TOTAL_ISSUES issue(s) in $FAILED_CHECKS check(s)${NC}"
        echo ""
        exit 1
    fi
}

# Run main function
main "$@"

