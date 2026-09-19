#!/usr/bin/env bats
# Integration tests for plugin management

load '../helpers/bats-support/load'
load '../helpers/bats-assert/load'

setup() {
    TEST_DIR="$(mktemp -d)"
    export PROJECT_DIR="$TEST_DIR"
    cd "$TEST_DIR" || exit 1

    mkdir -p scripts plugins data/plugins backups/plugins
}

teardown() {
    rm -rf "$TEST_DIR"
}

@test "plugin-manager lists plugins" {
    skip "Requires plugin-manager.sh"
}

@test "plugin-manager installs plugin from file" {
    skip "Requires plugin-manager.sh and test plugin"
}

@test "plugin-manager enables/disables plugins" {
    skip "Requires plugin-manager.sh"
}

