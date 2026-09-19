#!/usr/bin/env bats
# Integration tests for backup system

load '../helpers/bats-support/load'
load '../helpers/bats-assert/load'

setup() {
    TEST_DIR="$(mktemp -d)"
    export PROJECT_DIR="$TEST_DIR"
    cd "$TEST_DIR" || exit 1

    mkdir -p scripts config data/world backups logs
    # Create test world structure
    touch data/world/level.dat
    echo "test data" > data/world/test.txt
}

teardown() {
    rm -rf "$TEST_DIR"
}

@test "backup creates tar.gz file" {
    skip "Requires manage.sh backup functionality"
}

@test "backup includes world data" {
    skip "Requires manage.sh backup functionality"
}

@test "backup verification works" {
    skip "Requires manage.sh backup functionality"
}

@test "cleanup-backups removes old backups" {
    skip "Requires cleanup-backups.sh"
}

