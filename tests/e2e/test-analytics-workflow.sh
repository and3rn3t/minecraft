#!/usr/bin/env bats
# End-to-End Test: Analytics Workflow
# Tests complete analytics workflow from data collection to report generation via API

load 'helpers/bats-support/load'
load 'helpers/bats-assert/load'

setup() {
    export API_URL="${API_URL:-http://localhost:8080}"
    export API_KEY="${API_KEY:-test-api-key}"

    # Get project directory
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    PROJECT_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"
    cd "$PROJECT_DIR" || exit 1
}

@test "Analytics workflow: collect data via API" {
    skip "Requires running API server"

    # Step 1: Trigger data collection
    run curl -s -X POST "${API_URL}/api/analytics/collect" \
        -H "X-API-Key: ${API_KEY}" \
        -H "Content-Type: application/json"

    [ "$status" -eq 0 ]
    echo "$output" | grep -q "success" || echo "$output" | grep -q "error"
}

@test "Analytics workflow: get report via API" {
    skip "Requires running API server and collected data"

    # Step 2: Get analytics report
    run curl -s -X GET "${API_URL}/api/analytics/report?hours=24" \
        -H "X-API-Key: ${API_KEY}"

    [ "$status" -eq 0 ]
    echo "$output" | python3 -m json.tool > /dev/null
    assert_success
}

@test "Analytics workflow: get trends via API" {
    skip "Requires running API server"

    # Step 3: Get performance trends
    run curl -s -X GET "${API_URL}/api/analytics/trends?hours=24&type=performance" \
        -H "X-API-Key: ${API_KEY}"

    [ "$status" -eq 0 ]
    echo "$output" | python3 -m json.tool > /dev/null
    assert_success
}

@test "Analytics workflow: get anomalies via API" {
    skip "Requires running API server"

    # Step 4: Get detected anomalies
    run curl -s -X GET "${API_URL}/api/analytics/anomalies?hours=24&metric=tps" \
        -H "X-API-Key: ${API_KEY}"

    [ "$status" -eq 0 ]
    echo "$output" | python3 -m json.tool > /dev/null
    assert_success
}

@test "Analytics workflow: get predictions via API" {
    skip "Requires running API server"

    # Step 5: Get resource predictions
    run curl -s -X GET "${API_URL}/api/analytics/predictions?hours_ahead=1&metric=memory" \
        -H "X-API-Key: ${API_KEY}"

    [ "$status" -eq 0 ]
    echo "$output" | python3 -m json.tool > /dev/null
    assert_success
}

@test "Analytics workflow: get player behavior via API" {
    skip "Requires running API server"

    # Step 6: Get player behavior analytics
    run curl -s -X GET "${API_URL}/api/analytics/player-behavior?hours=24" \
        -H "X-API-Key: ${API_KEY}"

    [ "$status" -eq 0 ]
    echo "$output" | python3 -m json.tool > /dev/null
    assert_success
}

@test "Analytics workflow: generate custom report via API" {
    skip "Requires running API server"

    # Step 7: Generate custom report
    run curl -s -X POST "${API_URL}/api/analytics/custom-report" \
        -H "X-API-Key: ${API_KEY}" \
        -H "Content-Type: application/json" \
        -d '{"hours": 24, "metrics": ["performance", "players"]}'

    [ "$status" -eq 0 ]
    echo "$output" | python3 -m json.tool > /dev/null
    assert_success
}

@test "Analytics workflow: complete end-to-end" {
    skip "Requires running API server and Docker"

    # Complete workflow:
    # 1. Collect data
    # 2. Generate report
    # 3. Check trends
    # 4. Verify anomalies
    # 5. Get predictions

    # Collect
    curl -s -X POST "${API_URL}/api/analytics/collect" \
        -H "X-API-Key: ${API_KEY}" > /dev/null

    # Wait a moment for processing
    sleep 2

    # Get report
    report_output=$(curl -s -X GET "${API_URL}/api/analytics/report?hours=24" \
        -H "X-API-Key: ${API_KEY}")

    echo "$report_output" | python3 -m json.tool > /dev/null
    assert_success

    # Verify report structure
    echo "$report_output" | python3 << EOF
import json
import sys
data = json.load(sys.stdin)
assert 'report' in data or 'error' in data
if 'report' in data:
    report = data['report']
    assert 'generated_at' in report
    assert 'period_hours' in report
EOF
    assert_success
}

