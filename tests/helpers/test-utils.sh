#!/bin/bash
# Test Utilities
# Common functions and helpers for tests

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get project root directory
get_project_root() {
    local script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
    echo "$script_dir"
}

# Create temporary test directory
create_test_dir() {
    local test_dir=$(mktemp -d)
    echo "$test_dir"
}

# Cleanup test directory
cleanup_test_dir() {
    local test_dir="$1"
    if [ -d "$test_dir" ]; then
        rm -rf "$test_dir"
    fi
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Wait for server to be ready
wait_for_server() {
    local url="$1"
    local max_attempts="${2:-30}"
    local attempt=0

    while [ $attempt -lt $max_attempts ]; do
        if curl -s -f "$url" >/dev/null 2>&1; then
            return 0
        fi
        attempt=$((attempt + 1))
        sleep 1
    done

    return 1
}

# Create test backup file
create_test_backup() {
    local backup_dir="$1"
    local backup_name="${2:-test_backup_$(date +%Y%m%d_%H%M%S).tar.gz}"
    local backup_file="${backup_dir}/${backup_name}"

    # Create a simple test backup
    mkdir -p "${backup_dir}/test_data"
    echo "test content" > "${backup_dir}/test_data/test.txt"
    tar -czf "$backup_file" -C "${backup_dir}/test_data" .
    rm -rf "${backup_dir}/test_data"

    echo "$backup_file"
}

# Verify backup file
verify_backup() {
    local backup_file="$1"

    if [ ! -f "$backup_file" ]; then
        return 1
    fi

    # Check if it's a valid tar.gz
    if ! tar -tzf "$backup_file" >/dev/null 2>&1; then
        return 1
    fi

    return 0
}

# Create test API key
create_test_api_key() {
    local api_url="$1"
    local key_name="${2:-test-key-$(date +%s)}"

    # This would call the API to create a key
    # For now, return a mock key
    echo "test-api-key-${key_name}"
}

# Get API token from login
get_api_token() {
    local api_url="$1"
    local username="$2"
    local password="$3"

    # This would call the login endpoint
    # For now, return a mock token
    echo "test-token-${username}"
}

# Make authenticated API request
api_request() {
    local method="$1"
    local endpoint="$2"
    local token="$3"
    local data="${4:-}"

    local url="${API_URL:-http://localhost:8080}${endpoint}"
    local headers=(-H "Content-Type: application/json")

    if [ -n "$token" ]; then
        headers+=(-H "Authorization: Bearer ${token}")
    fi

    if [ -n "$data" ]; then
        curl -s -X "$method" "$url" "${headers[@]}" -d "$data"
    else
        curl -s -X "$method" "$url" "${headers[@]}"
    fi
}

# Check if server is running
is_server_running() {
    local pid_file="${1:-/tmp/minecraft-server.pid}"

    if [ ! -f "$pid_file" ]; then
        return 1
    fi

    local pid=$(cat "$pid_file")
    if ! kill -0 "$pid" 2>/dev/null; then
        return 1
    fi

    return 0
}

# Create test configuration
create_test_config() {
    local config_dir="$1"
    local config_name="$2"
    local config_content="$3"

    mkdir -p "$config_dir"
    echo "$config_content" > "${config_dir}/${config_name}"
    echo "${config_dir}/${config_name}"
}

# Assert file exists
assert_file_exists() {
    local file="$1"
    if [ ! -f "$file" ]; then
        echo "Error: File does not exist: $file" >&2
        return 1
    fi
    return 0
}

# Assert file contains text
assert_file_contains() {
    local file="$1"
    local text="$2"

    if ! grep -q "$text" "$file" 2>/dev/null; then
        echo "Error: File does not contain text: $text" >&2
        return 1
    fi
    return 0
}

# Assert directory exists
assert_dir_exists() {
    local dir="$1"
    if [ ! -d "$dir" ]; then
        echo "Error: Directory does not exist: $dir" >&2
        return 1
    fi
    return 0
}

