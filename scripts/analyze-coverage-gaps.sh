#!/bin/bash
# Analyze Coverage Gaps
# Identifies untested code paths and suggests test improvements

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

# Coverage files
COVERAGE_JSON="${PROJECT_DIR}/coverage.json"
COVERAGE_HTML="${PROJECT_DIR}/htmlcov/index.html"
GAP_REPORT="${PROJECT_DIR}/coverage-gaps.txt"

# Function to print header
print_header() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
}

# Function to check if coverage file exists
check_coverage_file() {
    if [ ! -f "$COVERAGE_JSON" ]; then
        echo -e "${YELLOW}Coverage file not found. Running tests with coverage...${NC}"
        cd "$PROJECT_DIR/tests/api"
        pytest -v \
            --cov=../../api \
            --cov-config=../../.coverage-config.ini \
            --cov-report=json \
            --cov-report=html
        cd "$PROJECT_DIR"
    fi

    if [ ! -f "$COVERAGE_JSON" ]; then
        echo -e "${RED}Error: Could not generate coverage file${NC}"
        exit 1
    fi
}

# Function to analyze coverage gaps
analyze_gaps() {
    print_header "Analyzing Coverage Gaps"

    check_coverage_file

    python3 << EOF
import json
from pathlib import Path

coverage_file = Path("$COVERAGE_JSON")
gap_report = Path("$GAP_REPORT")

if not coverage_file.exists():
    print("Coverage file not found")
    exit(1)

with open(coverage_file, 'r') as f:
    report = json.load(f)

files = report.get('files', {})
gaps = []

for file_path, file_data in files.items():
    if 'api/' not in file_path:
        continue

    summary = file_data.get('summary', {})
    percent_covered = summary.get('percent_covered', 0)
    covered_lines = summary.get('covered_lines', 0)
    num_statements = summary.get('num_statements', 0)

    if percent_covered < 80:
        gaps.append({
            'file': file_path,
            'coverage': percent_covered,
            'covered': covered_lines,
            'total': num_statements,
            'missing': num_statements - covered_lines
        })

# Sort by coverage percentage (lowest first)
gaps.sort(key=lambda x: x['coverage'])

# Write gap report
with open(gap_report, 'w') as f:
    f.write("Coverage Gap Analysis\n")
    f.write("=" * 60 + "\n\n")

    if not gaps:
        f.write("No significant coverage gaps found!\n")
        f.write("All files have >80% coverage.\n")
    else:
        f.write(f"Found {len(gaps)} files with coverage < 80%\n\n")

        for gap in gaps:
            f.write(f"File: {gap['file']}\n")
            f.write(f"  Coverage: {gap['coverage']:.1f}%\n")
            f.write(f"  Covered: {gap['covered']}/{gap['total']} lines\n")
            f.write(f"  Missing: {gap['missing']} lines\n")
            f.write("\n")

print(f"Gap analysis complete. Report saved to: {gap_report}")
EOF

    echo ""
    echo -e "${GREEN}Coverage gap analysis complete!${NC}"
    echo -e "${BLUE}Report saved to: $GAP_REPORT${NC}"
}

# Function to show detailed gaps
show_detailed_gaps() {
    print_header "Detailed Coverage Gaps"

    check_coverage_file

    python3 << EOF
import json
from pathlib import Path

coverage_file = Path("$COVERAGE_JSON")

with open(coverage_file, 'r') as f:
    report = json.load(f)

files = report.get('files', {})

print("Files with coverage < 80%:")
print("-" * 60)

for file_path, file_data in sorted(files.items()):
    if 'api/' not in file_path:
        continue

    summary = file_data.get('summary', {})
    percent_covered = summary.get('percent_covered', 0)

    if percent_covered < 80:
        covered = summary.get('covered_lines', 0)
        total = summary.get('num_statements', 0)
        missing = total - covered

        print(f"\n{file_path}")
        print(f"  Coverage: {percent_covered:.1f}%")
        print(f"  Lines: {covered}/{total} ({missing} missing)")

        # Show missing lines if available
        missing_lines = file_data.get('missing_lines', [])
        if missing_lines:
            print(f"  Missing line numbers: {', '.join(map(str, missing_lines[:20]))}")
            if len(missing_lines) > 20:
                print(f"  ... and {len(missing_lines) - 20} more")
EOF
}

# Function to suggest test improvements
suggest_improvements() {
    print_header "Test Improvement Suggestions"

    check_coverage_file

    python3 << EOF
import json
from pathlib import Path

coverage_file = Path("$COVERAGE_JSON")

with open(coverage_file, 'r') as f:
    report = json.load(f)

files = report.get('files', {})
suggestions = []

for file_path, file_data in files.items():
    if 'api/' not in file_path:
        continue

    summary = file_data.get('summary', {})
    percent_covered = summary.get('percent_covered', 0)

    if percent_covered < 80:
        file_name = Path(file_path).stem
        suggestions.append({
            'file': file_name,
            'coverage': percent_covered,
            'suggestion': f"Add tests for {file_name} to increase coverage from {percent_covered:.1f}% to 80%+"
        })

if suggestions:
    print("Suggested test improvements:")
    print("-" * 60)
    for suggestion in suggestions:
        print(f"• {suggestion['suggestion']}")
else:
    print("All files have good coverage! No suggestions needed.")
EOF
}

# Main function
main() {
    local command="${1:-analyze}"

    case "$command" in
        analyze)
            analyze_gaps
            ;;
        detailed)
            show_detailed_gaps
            ;;
        suggest)
            suggest_improvements
            ;;
        *)
            echo -e "${BLUE}Coverage Gap Analysis${NC}"
            echo ""
            echo "Usage: $0 {analyze|detailed|suggest}"
            echo ""
            echo "Commands:"
            echo "  analyze   - Analyze coverage gaps and generate report (default)"
            echo "  detailed  - Show detailed gap information"
            echo "  suggest   - Suggest test improvements"
            exit 1
            ;;
    esac
}

# Run main function
main "$@"

