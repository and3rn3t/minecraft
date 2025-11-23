#!/bin/bash
# Check Code Coverage Thresholds
# Validates that code coverage meets minimum requirements

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

# Coverage configuration
COVERAGE_THRESHOLD=${COVERAGE_THRESHOLD:-60}
COVERAGE_FILE="${PROJECT_DIR}/coverage.json"

# Function to print header
print_header() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
}

# Function to check coverage
check_coverage() {
    print_header "Code Coverage Check"

    if [ ! -f "$COVERAGE_FILE" ]; then
        echo -e "${YELLOW}Coverage file not found. Running tests with coverage...${NC}"
        cd "$PROJECT_DIR/tests/api"
        pytest -v \
            --cov=../../api \
            --cov-config=../../.coverage-config.ini \
            --cov-report=json \
            --cov-report=term-missing
        cd "$PROJECT_DIR"
    fi

    if [ ! -f "$COVERAGE_FILE" ]; then
        echo -e "${RED}Error: Could not generate coverage file${NC}"
        exit 1
    fi

    # Extract coverage percentage
    local coverage=$(python3 << EOF
import json
try:
    with open("$COVERAGE_FILE", 'r') as f:
        report = json.load(f)
    coverage = report.get('totals', {}).get('percent_covered', 0)
    print(f"{coverage:.2f}")
except Exception as e:
    print("0.00")
EOF
)

    echo -e "${BLUE}Current Coverage: ${coverage}%${NC}"
    echo -e "${BLUE}Required Threshold: ${COVERAGE_THRESHOLD}%${NC}"
    echo ""

    # Compare with threshold
    if (( $(echo "$coverage >= $COVERAGE_THRESHOLD" | bc -l) )); then
        echo -e "${GREEN}✓ Coverage meets threshold!${NC}"
        return 0
    else
        echo -e "${RED}✗ Coverage below threshold!${NC}"
        local diff=$(echo "$COVERAGE_THRESHOLD - $coverage" | bc)
        echo -e "${YELLOW}Need ${diff}% more coverage${NC}"
        return 1
    fi
}

# Function to show coverage report
show_report() {
    print_header "Coverage Report"

    if [ ! -f "$COVERAGE_FILE" ]; then
        echo -e "${YELLOW}Coverage file not found. Run check-coverage first.${NC}"
        exit 1
    fi

    python3 << EOF
import json

with open("$COVERAGE_FILE", 'r') as f:
    report = json.load(f)

totals = report.get('totals', {})
files = report.get('files', {})

print(f"Total Coverage: {totals.get('percent_covered', 0):.2f}%")
print(f"Lines Covered: {totals.get('covered_lines', 0)} / {totals.get('num_statements', 0)}")
print(f"Branches Covered: {totals.get('covered_branches', 0)} / {totals.get('num_branches', 0)}")
print("")
print("File Coverage:")
print("-" * 60)

for file_path, file_data in sorted(files.items()):
    if 'api/' in file_path:
        coverage = file_data.get('summary', {}).get('percent_covered', 0)
        lines = file_data.get('summary', {}).get('covered_lines', 0)
        total = file_data.get('summary', {}).get('num_statements', 0)
        print(f"{file_path:50} {coverage:6.1f}% ({lines}/{total})")
EOF
}

# Main function
main() {
    local command="${1:-check}"

    case "$command" in
        check)
            check_coverage
            ;;
        report)
            show_report
            ;;
        threshold)
            echo -e "${BLUE}Current threshold: ${COVERAGE_THRESHOLD}%${NC}"
            echo "Set COVERAGE_THRESHOLD environment variable to change"
            ;;
        *)
            echo -e "${BLUE}Code Coverage Check${NC}"
            echo ""
            echo "Usage: $0 {check|report|threshold}"
            echo ""
            echo "Commands:"
            echo "  check     - Check if coverage meets threshold (default)"
            echo "  report    - Show detailed coverage report"
            echo "  threshold - Show current threshold"
            echo ""
            echo "Environment Variables:"
            echo "  COVERAGE_THRESHOLD=${COVERAGE_THRESHOLD} - Minimum coverage percentage"
            exit 1
            ;;
    esac
}

# Check for bc (required for calculations)
if ! command -v bc >/dev/null 2>&1; then
    echo -e "${YELLOW}Warning: 'bc' not found. Install for threshold checking.${NC}"
fi

# Run main function
main "$@"

