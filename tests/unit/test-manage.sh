#!/usr/bin/env bats
# Unit tests for manage.sh script

load '../helpers/bats-support/load'
load '../helpers/bats-assert/load'

setup() {
    # Setup test environment
    TEST_DIR="$(mktemp -d)"
    export PROJECT_DIR="$TEST_DIR"
    cd "$TEST_DIR" || exit 1

    # Create minimal project structure
    mkdir -p scripts config data backups logs
}

teardown() {
    # Cleanup
    rm -rf "$TEST_DIR"
}

@test "manage.sh shows usage when no arguments" {
    # This test would require the actual manage.sh script
    # For now, we'll test the structure
    skip "Requires manage.sh in test environment"
}

@test "manage.sh usage function displays help" {
    skip "Requires manage.sh in test environment"
}

