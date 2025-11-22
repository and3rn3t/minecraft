#!/usr/bin/env bats
# Unit tests for backup-scheduler.sh

load '../helpers/bats-support/load'
load '../helpers/bats-assert/load'

setup() {
    TEST_DIR="$(mktemp -d)"
    export PROJECT_DIR="$TEST_DIR"
    cd "$TEST_DIR" || exit 1

    mkdir -p scripts config logs backups
    mkdir -p data/world
}

teardown() {
    rm -rf "$TEST_DIR"
}

@test "backup-scheduler respects BACKUP_ENABLED=false" {
    skip "Requires backup-scheduler.sh"
}

@test "backup-scheduler runs on daily schedule" {
    skip "Requires backup-scheduler.sh"
}

