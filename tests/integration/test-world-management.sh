#!/usr/bin/env bats
# Integration tests for world management

load '../helpers/bats-support/load'
load '../helpers/bats-assert/load'

setup() {
    TEST_DIR="$(mktemp -d)"
    export PROJECT_DIR="$TEST_DIR"
    cd "$TEST_DIR" || exit 1

    mkdir -p scripts data config/worlds config/world-templates
    touch server.properties
    echo "level-name=world" >> server.properties
}

teardown() {
    rm -rf "$TEST_DIR"
}

@test "world-manager lists worlds" {
    skip "Requires world-manager.sh"
}

@test "world-manager creates new world" {
    skip "Requires world-manager.sh"
}

@test "world-manager switches worlds" {
    skip "Requires world-manager.sh"
}

@test "world-manager monitors world sizes" {
    skip "Requires world-manager.sh"
}

