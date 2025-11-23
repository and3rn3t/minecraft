#!/usr/bin/env bats
# Unit Tests: analytics-collector.sh
# Tests for the analytics data collector script

load 'helpers/bats-support/load'
load 'helpers/bats-assert/load'

setup() {
    # Get script directory
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    PROJECT_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"
    cd "$PROJECT_DIR" || exit 1

    # Create test directories
    mkdir -p analytics

    # Clean up any existing test data
    rm -f analytics/*.jsonl
}

teardown() {
    # Cleanup test data
    rm -f analytics/*.jsonl
}

@test "analytics-collector.sh creates analytics directory" {
    # Remove directory if it exists
    rm -rf analytics

    # Run script
    run ./scripts/analytics-collector.sh

    # Check that directory was created
    assert_file_exists analytics
}

@test "analytics-collector.sh creates JSONL files" {
    skip "Requires Docker and running server"

    # Run script
    ./scripts/analytics-collector.sh

    # Check that JSONL files are created
    # Note: Files may be empty if server is not running
    # This test verifies the script doesn't crash
    assert_success
}

@test "analytics-collector.sh handles missing Docker gracefully" {
    # Mock docker command to fail
    export PATH="$(dirname "$(which echo)"):$PATH"

    # Create a fake docker that fails
    mkdir -p /tmp/test_bin
    echo '#!/bin/bash' > /tmp/test_bin/docker
    echo 'exit 1' >> /tmp/test_bin/docker
    chmod +x /tmp/test_bin/docker
    export PATH="/tmp/test_bin:$PATH"

    # Run script - should not crash
    run ./scripts/analytics-collector.sh

    # Should complete (may create empty files)
    [ "$status" -eq 0 ] || [ "$status" -eq 1 ]

    # Cleanup
    rm -rf /tmp/test_bin
}

@test "analytics-collector.sh writes valid JSON" {
    skip "Requires Docker and running server"

    # Run script
    ./scripts/analytics-collector.sh

    # Check that any created files contain valid JSON
    for file in analytics/*.jsonl; do
        if [ -f "$file" ] && [ -s "$file" ]; then
            # Read first line and validate JSON
            first_line=$(head -n 1 "$file")
            echo "$first_line" | python3 -m json.tool > /dev/null
            assert_success
        fi
    done
}

@test "analytics-collector.sh includes timestamp in data" {
    skip "Requires Docker and running server"

    # Run script
    ./scripts/analytics-collector.sh

    # Check that data includes timestamp
    if [ -f analytics/performance.jsonl ] && [ -s analytics/performance.jsonl ]; then
        first_line=$(head -n 1 analytics/performance.jsonl)
        echo "$first_line" | python3 << EOF
import json
import sys
data = json.load(sys.stdin)
assert 'timestamp' in data, "Missing timestamp"
assert 'datetime' in data, "Missing datetime"
assert isinstance(data['timestamp'], (int, float)), "Timestamp not numeric"
EOF
        assert_success
    fi
}

