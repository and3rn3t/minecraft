#!/bin/bash
# Generate Release Notes from CHANGELOG.md
# Extracts release notes for a specific version

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
CHANGELOG="${PROJECT_DIR}/CHANGELOG.md"

# Function to print usage
usage() {
    echo -e "${BLUE}Generate Release Notes${NC}"
    echo ""
    echo "Usage: $0 <version> [output_file]"
    echo ""
    echo "Arguments:"
    echo "  version     - Version number (e.g., 1.4.0)"
    echo "  output_file - Optional output file (default: stdout)"
    echo ""
    echo "Examples:"
    echo "  $0 1.4.0"
    echo "  $0 1.4.0 release-notes.md"
    exit 1
}

# Function to extract release notes
extract_release_notes() {
    local version="$1"
    local output_file="$2"

    if [ ! -f "$CHANGELOG" ]; then
        echo -e "${RED}Error: CHANGELOG.md not found${NC}" >&2
        exit 1
    fi

    # Use Python to extract release notes
    python3 << EOF
import re
import sys

version = "$version"
output_file = "$output_file" if "$output_file" else None

try:
    with open("$CHANGELOG", 'r') as f:
        content = f.read()

    # Find the section for this version
    pattern = rf'## \[{re.escape(version)}\].*?(?=## \[|\Z)'
    match = re.search(pattern, content, re.DOTALL)

    if match:
        notes = match.group(0).strip()
        # Remove the version header
        notes = re.sub(rf'## \[{re.escape(version)}\].*?\n', '', notes, count=1)

        if output_file:
            with open(output_file, 'w') as f:
                f.write(notes)
            print(f"Release notes written to {output_file}")
        else:
            print(notes)
    else:
        # Fallback: use Unreleased section
        pattern = r'## \[Unreleased\].*?(?=## \[|\Z)'
        match = re.search(pattern, content, re.DOTALL)
        if match:
            notes = match.group(0).strip()
            notes = re.sub(r'## \[Unreleased\].*?\n', '', notes, count=1)
            notes = f"## Changes in v{version}\n\n{notes}"

            if output_file:
                with open(output_file, 'w') as f:
                    f.write(notes)
                print(f"Release notes written to {output_file} (from Unreleased section)")
            else:
                print(notes)
        else:
            error_msg = f"Version {version} not found in CHANGELOG.md"
            if output_file:
                with open(output_file, 'w') as f:
                    f.write(f"## Changes in v{version}\n\nSee CHANGELOG.md for details.\n")
                print(f"Warning: {error_msg}. Created placeholder file.")
            else:
                print(f"## Changes in v{version}\n\nSee CHANGELOG.md for details.", file=sys.stderr)
                sys.exit(1)
except Exception as e:
    print(f"Error: {e}", file=sys.stderr)
    sys.exit(1)
EOF
}

# Main function
main() {
    if [ $# -lt 1 ]; then
        usage
    fi

    local version="$1"
    local output_file="${2:-}"

    # Validate version format (basic check)
    if ! echo "$version" | grep -qE '^[0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z0-9]+)?$'; then
        echo -e "${RED}Error: Invalid version format: $version${NC}" >&2
        echo "Expected format: X.Y.Z or X.Y.Z-prerelease" >&2
        exit 1
    fi

    extract_release_notes "$version" "$output_file"
}

# Run main function
main "$@"

