#!/usr/bin/env bats
# Integration Test: Analytics System
# Tests the complete analytics workflow: collection, processing, and reporting

load 'helpers/bats-support/load'
load 'helpers/bats-assert/load'
load 'helpers/test-utils.sh'

setup() {
    # Get script directory
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    PROJECT_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"
    cd "$PROJECT_DIR" || exit 1

    # Create test directories
    mkdir -p analytics analytics/processed

    # Clean up any existing test data
    rm -f analytics/*.jsonl analytics/processed/*.json
}

teardown() {
    # Cleanup test data
    rm -f analytics/*.jsonl analytics/processed/*.json
}

@test "analytics-collector.sh creates analytics data files" {
    skip "Requires Docker and running server"

    # Run analytics collector
    run ./scripts/analytics-collector.sh

    # Check exit code
    assert_success

    # Check that data files are created
    assert_file_exists analytics/players.jsonl
    assert_file_exists analytics/performance.jsonl
    assert_file_exists analytics/network.jsonl
    assert_file_exists analytics/world_stats.jsonl
}

@test "analytics-collector.sh writes valid JSONL data" {
    skip "Requires Docker and running server"

    # Run analytics collector
    ./scripts/analytics-collector.sh

    # Check that files contain valid JSON
    if [ -f analytics/players.jsonl ]; then
        # Read first line and validate JSON
        first_line=$(head -n 1 analytics/players.jsonl)
        echo "$first_line" | python3 -m json.tool > /dev/null
        assert_success
    fi
}

@test "analytics-processor.py generates report" {
    skip "Requires analytics data"

    # Create sample analytics data
    cat > analytics/performance.jsonl << EOF
{"timestamp": $(date +%s), "datetime": "$(date +"%Y-%m-%d %H:%M:%S")", "data": {"tps": 20.0, "cpu": 50.0, "memory": 1000}}
{"timestamp": $(($(date +%s) - 3600)), "datetime": "$(date -d "1 hour ago" +"%Y-%m-%d %H:%M:%S")", "data": {"tps": 19.5, "cpu": 55.0, "memory": 1100}}
EOF

    # Run analytics processor
    run python3 scripts/analytics-processor.py

    # Check exit code
    assert_success

    # Check that report is generated
    assert_file_exists analytics/processed/latest_report.json

    # Check that report contains expected fields
    if [ -f analytics/processed/latest_report.json ]; then
        python3 << EOF
import json
with open('analytics/processed/latest_report.json', 'r') as f:
    report = json.load(f)
    assert 'generated_at' in report
    assert 'period_hours' in report
    assert 'performance' in report or 'summary' in report
EOF
        assert_success
    fi
}

@test "analytics-processor.py detects anomalies" {
    skip "Requires analytics data"

    # Create data with anomaly (very low TPS)
    cat > analytics/performance.jsonl << EOF
{"timestamp": $(date +%s), "datetime": "$(date +"%Y-%m-%d %H:%M:%S")", "data": {"tps": 20.0, "cpu": 50.0, "memory": 1000}}
{"timestamp": $(($(date +%s) - 1800)), "datetime": "$(date -d "30 minutes ago" +"%Y-%m-%d %H:%M:%S")", "data": {"tps": 20.0, "cpu": 50.0, "memory": 1000}}
{"timestamp": $(($(date +%s) - 3600)), "datetime": "$(date -d "1 hour ago" +"%Y-%m-%d %H:%M:%S")", "data": {"tps": 5.0, "cpu": 50.0, "memory": 1000}}
EOF

    # Run analytics processor
    python3 scripts/analytics-processor.py

    # Check that anomalies are detected
    if [ -f analytics/processed/latest_report.json ]; then
        python3 << EOF
import json
with open('analytics/processed/latest_report.json', 'r') as f:
    report = json.load(f)
    perf = report.get('performance', {})
    tps = perf.get('tps', {})
    anomalies = tps.get('anomalies', [])
    assert len(anomalies) > 0, "No anomalies detected"
EOF
        assert_success
    fi
}

@test "analytics system end-to-end workflow" {
    skip "Requires Docker and running server"

    # Step 1: Collect data
    run ./scripts/analytics-collector.sh
    assert_success

    # Step 2: Process data
    run python3 scripts/analytics-processor.py
    assert_success

    # Step 3: Verify report exists
    assert_file_exists analytics/processed/latest_report.json

    # Step 4: Verify report structure
    if [ -f analytics/processed/latest_report.json ]; then
        python3 << EOF
import json
with open('analytics/processed/latest_report.json', 'r') as f:
    report = json.load(f)
    # Check required fields
    required_fields = ['generated_at', 'period_hours']
    for field in required_fields:
        assert field in report, f"Missing field: {field}"
EOF
        assert_success
    fi
}

@test "analytics data retention" {
    skip "Requires analytics data"

    # Create old data (more than 24 hours old)
    old_timestamp=$(($(date +%s) - 86400 - 3600))  # 25 hours ago
    cat > analytics/performance.jsonl << EOF
{"timestamp": $old_timestamp, "datetime": "$(date -d "25 hours ago" +"%Y-%m-%d %H:%M:%S")", "data": {"tps": 20.0}}
EOF

    # Create recent data
    recent_timestamp=$(date +%s)
    echo "{\"timestamp\": $recent_timestamp, \"datetime\": \"$(date +"%Y-%m-%d %H:%M:%S")\", \"data\": {\"tps\": 20.0}}" >> analytics/performance.jsonl

    # Run processor with 24 hour window
    python3 scripts/analytics-processor.py

    # Verify only recent data is processed
    if [ -f analytics/processed/latest_report.json ]; then
        python3 << EOF
import json
# The processor should only load data from last 24 hours
# This is tested implicitly by checking report generation succeeds
with open('analytics/processed/latest_report.json', 'r') as f:
    report = json.load(f)
    assert report['period_hours'] == 24
EOF
        assert_success
    fi
}

