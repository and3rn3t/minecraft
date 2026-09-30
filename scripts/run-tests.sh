#!/bin/bash
# Test Runner Script
#
# Runs the BATS suite (tests/unit) and the pytest suite (tests/api). CI's
# bash-tests job runs `run-tests.sh bash`.
#
# A missing runner is a failure, not a skip: a gate that reports success while
# running nothing is how placeholder tests here came to be trusted.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source-path=SCRIPTDIR
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
TESTS_DIR="${PROJECT_DIR}/tests"

FAILED_SUITES=()
RAN_SUITES=0

print_header() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
}

command_exists() {
    command -v "$1" >/dev/null 2>&1
}

install_dependencies() {
    echo -e "${BLUE}Installing test dependencies...${NC}"

    if ! command_exists bats; then
        if command_exists brew; then
            brew install bats-core
        elif command_exists apt-get; then
            sudo apt-get update && sudo apt-get install -y bats
        else
            echo -e "${YELLOW}Install bats manually: https://github.com/bats-core/bats-core${NC}"
        fi
    fi

    python3 -m pip install -r "${PROJECT_DIR}/api/requirements.txt" -r "${PROJECT_DIR}/api/requirements-test.txt"
}

# Every file in tests/unit, whatever its mode: bats reads the file itself, so
# the executable bit is irrelevant, and filtering on it once skipped suites
# silently.
run_bash_tests() {
    print_header "Running Bash Script Tests"
    RAN_SUITES=$((RAN_SUITES + 1))

    if ! command_exists bats; then
        echo -e "${RED}BATS is not installed (brew install bats-core), so nothing ran.${NC}"
        FAILED_SUITES+=("bash (bats missing)")
        return
    fi

    local files=("${TESTS_DIR}"/unit/*.sh)
    if [ ! -f "${files[0]}" ]; then
        echo -e "${RED}No BATS files found in tests/unit.${NC}"
        FAILED_SUITES+=("bash (no tests)")
        return
    fi

    if ! bats "${files[@]}"; then
        FAILED_SUITES+=("bash")
    fi
}

# Coverage flags, markers and the threshold come from tests/api/pytest.ini,
# which only applies when pytest runs from that directory.
run_python_tests() {
    print_header "Running Python/API Tests"
    RAN_SUITES=$((RAN_SUITES + 1))

    if ! python3 -c "import pytest" 2>/dev/null; then
        echo -e "${RED}pytest is not installed ($0 install-deps), so nothing ran.${NC}"
        FAILED_SUITES+=("api (pytest missing)")
        return
    fi

    local args=(-m "not performance")
    if python3 -c "import xdist" 2>/dev/null; then
        args+=(-n auto)
    fi

    if ! (cd "${TESTS_DIR}/api" && python3 -m pytest "${args[@]}"); then
        FAILED_SUITES+=("api")
    fi
}

show_summary() {
    echo ""
    print_header "Test Summary"

    if [ "$RAN_SUITES" -eq 0 ]; then
        echo -e "${RED}No suites were run${NC}"
        return 1
    fi

    if [ "${#FAILED_SUITES[@]}" -eq 0 ]; then
        echo -e "${GREEN}All ${RAN_SUITES} suite(s) passed${NC}"
        return 0
    fi

    echo -e "${RED}Failed: ${FAILED_SUITES[*]}${NC}"
    return 1
}

usage() {
    echo -e "${BLUE}Test Runner for Minecraft Server${NC}"
    echo ""
    echo "Usage: $0 [suite]"
    echo ""
    echo "Suites:"
    echo "  all           - BATS and pytest (default)"
    echo "  bash | unit   - BATS suite in tests/unit"
    echo "  api           - pytest suite in tests/api"
    echo ""
    echo "Other:"
    echo "  install-deps  - Install bats and the Python test dependencies"
    echo ""
    echo "Web tests run from web/: npm test (Vitest), npm run test:playwright."
    exit 1
}

main() {
    case "${1:-all}" in
        all)
            run_bash_tests
            run_python_tests
            ;;
        bash | unit)
            run_bash_tests
            ;;
        api)
            run_python_tests
            ;;
        install-deps)
            install_dependencies
            return
            ;;
        *)
            usage
            ;;
    esac
    show_summary
}

main "$@"
