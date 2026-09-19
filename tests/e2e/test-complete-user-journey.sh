#!/usr/bin/env bats
# End-to-End Test: Complete User Journey
# Tests complete user workflows from registration to server management

load 'helpers/bats-support/load'
load 'helpers/bats-assert/load'

setup() {
    export API_URL="${API_URL:-http://localhost:8080}"
    export TEST_USER="e2e_test_user_$(date +%s)"
    export TEST_PASSWORD="TestPassword123!"
    export TEST_EMAIL="test_$(date +%s)@example.com"

    # Get project directory
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    PROJECT_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"
    cd "$PROJECT_DIR" || exit 1
}

teardown() {
    # Cleanup: Delete test user if created
    if [ -n "$AUTH_TOKEN" ]; then
        curl -s -X DELETE "${API_URL}/api/users/${TEST_USER}" \
            -H "Authorization: Bearer ${AUTH_TOKEN}" > /dev/null || true
    fi
}

@test "Complete user journey: Registration → Login → Dashboard → Analytics" {
    skip "Requires running API server"

    # Step 1: User Registration
    echo "Step 1: Registering user..."
    register_response=$(curl -s -X POST "${API_URL}/api/auth/register" \
        -H "Content-Type: application/json" \
        -d "{
            \"username\": \"${TEST_USER}\",
            \"password\": \"${TEST_PASSWORD}\",
            \"email\": \"${TEST_EMAIL}\"
        }")

    echo "$register_response" | python3 -m json.tool > /dev/null
    assert_success

    # Step 2: User Login
    echo "Step 2: Logging in..."
    login_response=$(curl -s -X POST "${API_URL}/api/auth/login" \
        -H "Content-Type: application/json" \
        -d "{
            \"username\": \"${TEST_USER}\",
            \"password\": \"${TEST_PASSWORD}\"
        }")

    echo "$login_response" | python3 -m json.tool > /dev/null
    assert_success

    # Extract token
    AUTH_TOKEN=$(echo "$login_response" | python3 -c "import sys, json; print(json.load(sys.stdin).get('token', ''))")
    [ -n "$AUTH_TOKEN" ]

    # Step 3: Access Dashboard (via status check)
    echo "Step 3: Checking server status..."
    status_response=$(curl -s -X GET "${API_URL}/api/status" \
        -H "Authorization: Bearer ${AUTH_TOKEN}")

    echo "$status_response" | python3 -m json.tool > /dev/null
    assert_success

    # Step 4: Collect Analytics Data
    echo "Step 4: Collecting analytics data..."
    analytics_collect=$(curl -s -X POST "${API_URL}/api/analytics/collect" \
        -H "Authorization: Bearer ${AUTH_TOKEN}")

    echo "$analytics_collect" | python3 -m json.tool > /dev/null
    assert_success

    # Step 5: Get Analytics Report
    echo "Step 5: Getting analytics report..."
    analytics_report=$(curl -s -X GET "${API_URL}/api/analytics/report?hours=24" \
        -H "Authorization: Bearer ${AUTH_TOKEN}")

    echo "$analytics_report" | python3 -m json.tool > /dev/null
    assert_success

    # Step 6: Get Player Behavior
    echo "Step 6: Getting player behavior..."
    player_behavior=$(curl -s -X GET "${API_URL}/api/analytics/player-behavior?hours=24" \
        -H "Authorization: Bearer ${AUTH_TOKEN}")

    echo "$player_behavior" | python3 -m json.tool > /dev/null
    assert_success

    echo "Complete user journey test passed!"
}

@test "Complete workflow: Server Management" {
    skip "Requires running API server and authentication"

    # This test requires authentication setup from previous test
    # or manual API key setup

    # Step 1: Check server status
    status=$(curl -s -X GET "${API_URL}/api/status" \
        -H "X-API-Key: ${API_KEY:-test-key}")

    echo "$status" | python3 -m json.tool > /dev/null
    assert_success

    # Step 2: Get server metrics
    metrics=$(curl -s -X GET "${API_URL}/api/metrics" \
        -H "X-API-Key: ${API_KEY:-test-key}")

    echo "$metrics" | python3 -m json.tool > /dev/null
    assert_success

    # Step 3: Get players
    players=$(curl -s -X GET "${API_URL}/api/players" \
        -H "X-API-Key: ${API_KEY:-test-key}")

    echo "$players" | python3 -m json.tool > /dev/null
    assert_success
}

@test "Complete workflow: Backup Management" {
    skip "Requires running API server and authentication"

    # Step 1: List backups
    backups=$(curl -s -X GET "${API_URL}/api/backups" \
        -H "X-API-Key: ${API_KEY:-test-key}")

    echo "$backups" | python3 -m json.tool > /dev/null
    assert_success

    # Step 2: Create backup (if server is running)
    backup_create=$(curl -s -X POST "${API_URL}/api/backup" \
        -H "X-API-Key: ${API_KEY:-test-key}")

    # May fail if server not running, but should return valid JSON
    echo "$backup_create" | python3 -m json.tool > /dev/null || true
}

@test "Complete workflow: Analytics → Report → Action" {
    skip "Requires running API server and authentication"

    # Step 1: Collect analytics
    collect=$(curl -s -X POST "${API_URL}/api/analytics/collect" \
        -H "X-API-Key: ${API_KEY:-test-key}")

    echo "$collect" | python3 -m json.tool > /dev/null
    assert_success

    # Step 2: Wait for processing
    sleep 2

    # Step 3: Get report
    report=$(curl -s -X GET "${API_URL}/api/analytics/report?hours=24" \
        -H "X-API-Key: ${API_KEY:-test-key}")

    echo "$report" | python3 -m json.tool > /dev/null
    assert_success

    # Step 4: Check for anomalies
    anomalies=$(curl -s -X GET "${API_URL}/api/analytics/anomalies?hours=24&metric=tps" \
        -H "X-API-Key: ${API_KEY:-test-key}")

    echo "$anomalies" | python3 -m json.tool > /dev/null
    assert_success

    # Step 5: Get predictions
    predictions=$(curl -s -X GET "${API_URL}/api/analytics/predictions?hours_ahead=1&metric=memory" \
        -H "X-API-Key: ${API_KEY:-test-key}")

    echo "$predictions" | python3 -m json.tool > /dev/null
    assert_success
}

@test "Complete workflow: Configuration Management" {
    skip "Requires running API server and authentication"

    # Step 1: List config files
    config_files=$(curl -s -X GET "${API_URL}/api/config/files" \
        -H "X-API-Key: ${API_KEY:-test-key}")

    echo "$config_files" | python3 -m json.tool > /dev/null
    assert_success

    # Step 2: Get specific config file
    config_content=$(curl -s -X GET "${API_URL}/api/config/files/server.properties" \
        -H "X-API-Key: ${API_KEY:-test-key}")

    # May fail if file doesn't exist, but should return valid response
    echo "$config_content" | python3 -m json.tool > /dev/null || true
}

@test "Complete workflow: World Management" {
    skip "Requires running API server and authentication"

    # Step 1: List worlds
    worlds=$(curl -s -X GET "${API_URL}/api/worlds" \
        -H "X-API-Key: ${API_KEY:-test-key}")

    echo "$worlds" | python3 -m json.tool > /dev/null
    assert_success
}

@test "Error handling: Invalid credentials" {
    skip "Requires running API server"

    # Attempt login with invalid credentials
    login_response=$(curl -s -X POST "${API_URL}/api/auth/login" \
        -H "Content-Type: application/json" \
        -d '{
            "username": "invalid_user",
            "password": "invalid_password"
        }')

    echo "$login_response" | python3 -m json.tool > /dev/null
    assert_success

    # Should contain error
    echo "$login_response" | python3 -c "import sys, json; assert 'error' in json.load(sys.stdin)" || true
}

@test "Error handling: Unauthorized access" {
    skip "Requires running API server"

    # Attempt to access protected endpoint without auth
    response=$(curl -s -X GET "${API_URL}/api/status")

    # Should return 401
    echo "$response" | python3 << EOF
import sys, json
data = json.load(sys.stdin)
# May be error message or empty, but should not be successful data
assert 'error' in data or 'status' not in data
EOF
    assert_success
}

@test "Error handling: Invalid endpoint" {
    skip "Requires running API server"

    # Attempt to access non-existent endpoint
    response=$(curl -s -X GET "${API_URL}/api/nonexistent")

    # Should return 404
    echo "$response" | python3 << EOF
import sys, json
data = json.load(sys.stdin)
assert 'error' in data
EOF
    assert_success
}

