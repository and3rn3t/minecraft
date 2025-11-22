#!/usr/bin/env bats
# Unit tests for log-manager.sh

load '../helpers/bats-support/load'
load '../helpers/bats-assert/load'

setup() {
    TEST_DIR="$(mktemp -d)"
    export PROJECT_DIR="$TEST_DIR"
    cd "$TEST_DIR" || exit 1

    mkdir -p scripts config logs data/logs logs/index logs/archive
}

teedown() {
    rm -rf "$TEST_DIR"
}

@test "log-manager index creates index files" {
    skip "Requires log-manager.sh"
}

@test "log-manager rotate archives large logs" {
    skip "Requires log-manager.sh"
}

@test "log-manager errors detects error patterns" {
    skip "Requires log-manager.sh"
}

