#!/bin/bash
# Test Runner Script
# Runs all automated tests for the project

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
TESTS_DIR="${PROJECT_DIR}/tests"

# Test results
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# Function to print test header
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

# Function to install test dependencies
install_dependencies() {
    echo -e "${BLUE}Installing test dependencies...${NC}"

    # Install bats for bash testing
    if ! command_exists bats; then
        echo -e "${YELLOW}BATS not found. Installing...${NC}"
        if command_exists apt-get; then
            sudo apt-get update && sudo apt-get install -y bats
        elif command_exists brew; then
            brew install bats-core
        else
            echo -e "${YELLOW}Please install bats manually: https://github.com/bats-core/bats-core${NC}"
        fi
    fi

    # Install Python test dependencies
    if command_exists python3; then
        echo -e "${BLUE}Installing Python test dependencies...${NC}"
        python3 -m pip install --user pytest pytest-cov requests 2>/dev/null || {
            echo -e "${YELLOW}Warning: Failed to install Python dependencies${NC}"
            echo -e "${YELLOW}Try: pip3 install pytest pytest-cov requests${NC}"
        }
    fi

    echo -e "${GREEN}Dependencies installed${NC}"
}

# Function to run bash tests
run_bash_tests() {
    print_header "Running Bash Script Tests"

    if ! command_exists bats; then
        echo -e "${YELLOW}BATS not installed. Skipping bash tests.${NC}"
        echo -e "${YELLOW}Run: $0 install-deps${NC}"
        return 0
    fi

    local test_count=0
    local pass_count=0
    local fail_count=0

    # Find all .sh test files
    for test_file in "${TESTS_DIR}"/unit/*.sh "${TESTS_DIR}"/integration/*.sh; do
        if [ -f "$test_file" ] && [ -x "$test_file" ]; then
            echo -e "${BLUE}Running: $(basename "$test_file")${NC}"
            if bats "$test_file"; then
                pass_count=$((pass_count + 1))
            else
                fail_count=$((fail_count + 1))
            fi
            test_count=$((test_count + 1))
        fi
    done

    TOTAL_TESTS=$((TOTAL_TESTS + test_count))
    PASSED_TESTS=$((PASSED_TESTS + pass_count))
    FAILED_TESTS=$((FAILED_TESTS + fail_count))

    echo ""
    echo -e "${BLUE}Bash Tests: $pass_count passed, $fail_count failed${NC}"
}

# Function to run Python tests
run_python_tests() {
    print_header "Running Python/API Tests"

    if ! command_exists python3; then
        echo -e "${YELLOW}Python 3 not found. Skipping Python tests.${NC}"
        return 0
    fi

    if ! python3 -c "import pytest" 2>/dev/null; then
        echo -e "${YELLOW}pytest not installed. Skipping Python tests.${NC}"
        echo -e "${YELLOW}Run: $0 install-deps${NC}"
        return 0
    fi

    cd "$PROJECT_DIR"

    # Check for parallel execution support
    local parallel_flag=""
    if python3 -c "import xdist" 2>/dev/null; then
        # Use auto-detection of CPU count, or specify with -n auto
        parallel_flag="-n auto"
        echo -e "${BLUE}Running tests in parallel mode${NC}"
    fi

    # Run pytest with coverage
    local pytest_args=("tests/api/" "-v")

    if python3 -c "import pytest_cov" 2>/dev/null; then
        pytest_args+=("--cov=api" "--cov-config=.coverage-config.ini" "--cov-report=term-missing" "--cov-report=html" "--cov-report=json" "--cov-report=xml")
    fi

    if [ -n "$parallel_flag" ]; then
        pytest_args+=($parallel_flag)
    fi

    python3 -m pytest "${pytest_args[@]}"

    local exit_code=$?

    if [ $exit_code -eq 0 ]; then
        PASSED_TESTS=$((PASSED_TESTS + 1))
    else
        FAILED_TESTS=$((FAILED_TESTS + 1))
    fi
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
}

# Function to run unit tests
run_unit_tests() {
    print_header "Running Unit Tests"

    # Bash unit tests
    if command_exists bats; then
        for test_file in "${TESTS_DIR}"/unit/*.sh; do
            if [ -f "$test_file" ] && [ -x "$test_file" ]; then
                echo -e "${BLUE}Running: $(basename "$test_file")${NC}"
                bats "$test_file" || true
            fi
        done
    fi

    # Python unit tests
    if command_exists python3 && python3 -c "import pytest" 2>/dev/null; then
        cd "$PROJECT_DIR"
        python3 -m pytest tests/api/ -v -k "test_" || true
    fi
}

# Function to run integration tests
run_integration_tests() {
    print_header "Running Integration Tests"

    if ! command_exists bats; then
        echo -e "${YELLOW}BATS not installed. Skipping integration tests.${NC}"
        return 0
    fi

    for test_file in "${TESTS_DIR}"/integration/*.sh; do
        if [ -f "$test_file" ] && [ -x "$test_file" ]; then
            echo -e "${BLUE}Running: $(basename "$test_file")${NC}"
            bats "$test_file" || true
        fi
    done
}

# Function to run API tests
run_api_tests() {
    print_header "Running API Tests"
    run_python_tests
}

# Function to run E2E tests
run_e2e_tests() {
    print_header "Running End-to-End Tests"

    if ! command_exists bats; then
        echo -e "${YELLOW}BATS not installed. Skipping E2E tests.${NC}"
        echo -e "${YELLOW}Run: $0 install-deps${NC}"
        return 0
    fi

    local test_count=0
    local pass_count=0
    local fail_count=0

    # Find all E2E test files
    if [ -d "${TESTS_DIR}/e2e" ]; then
        for test_file in "${TESTS_DIR}"/e2e/*.sh; do
            if [ -f "$test_file" ] && [ -x "$test_file" ]; then
                echo -e "${BLUE}Running: $(basename "$test_file")${NC}"
                if bats "$test_file"; then
                    pass_count=$((pass_count + 1))
                else
                    fail_count=$((fail_count + 1))
                fi
                test_count=$((test_count + 1))
            fi
        done
    else
        echo -e "${YELLOW}No E2E tests directory found${NC}"
    fi

    TOTAL_TESTS=$((TOTAL_TESTS + test_count))
    PASSED_TESTS=$((PASSED_TESTS + pass_count))
    FAILED_TESTS=$((FAILED_TESTS + fail_count))

    echo ""
    echo -e "${BLUE}E2E Tests: $pass_count passed, $fail_count failed${NC}"
}

# Function to show test summary
show_summary() {
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}Test Summary${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo -e "Total: $TOTAL_TESTS"
    echo -e "${GREEN}Passed: $PASSED_TESTS${NC}"
    if [ $FAILED_TESTS -gt 0 ]; then
        echo -e "${RED}Failed: $FAILED_TESTS${NC}"
    else
        echo -e "${GREEN}Failed: $FAILED_TESTS${NC}"
    fi
    echo ""

    if [ $FAILED_TESTS -eq 0 ] && [ $TOTAL_TESTS -gt 0 ]; then
        echo -e "${GREEN}All tests passed!${NC}"
        return 0
    elif [ $TOTAL_TESTS -eq 0 ]; then
        echo -e "${YELLOW}No tests were run${NC}"
        return 0
    else
        echo -e "${RED}Some tests failed${NC}"
        return 1
    fi
}

# Function to display usage
usage() {
    echo -e "${BLUE}Test Runner for Minecraft Server${NC}"
    echo ""
    echo "Usage: $0 [suite] [options]"
    echo ""
    echo "Test Suites:"
    echo "  all           - Run all tests (default)"
    echo "  unit          - Run unit tests only"
    echo "  integration   - Run integration tests only"
    echo "  api           - Run API tests only"
    echo "  e2e           - Run end-to-end tests only"
    echo "  bash          - Run bash script tests only"
    echo ""
    echo "Options:"
    echo "  install-deps - Install test dependencies"
    echo "  verbose      - Verbose output"
    echo ""
    exit 1
}

# Main function
main() {
    case "${1:-all}" in
        all)
            run_bash_tests
            run_python_tests
            run_e2e_tests
            show_summary
            ;;
        unit)
            run_unit_tests
            show_summary
            ;;
        integration)
            run_integration_tests
            show_summary
            ;;
        api)
            run_api_tests
            show_summary
            ;;
        e2e)
            run_e2e_tests
            show_summary
            ;;
        bash)
            run_bash_tests
            show_summary
            ;;
        install-deps)
            install_dependencies
            ;;
        *)
            usage
            ;;
    esac
}

# Run main function
main "$@"

