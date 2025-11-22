#!/usr/bin/env bats
# Integration tests for RCON

load '../helpers/bats-support/load'
load '../helpers/bats-assert/load'

setup() {
    TEST_DIR="$(mktemp -d)"
    export PROJECT_DIR="$TEST_DIR"
    cd "$TEST_DIR" || exit 1

    mkdir -p scripts config
    touch server.properties
}

teardown() {
    rm -rf "$TEST_DIR"
}

@test "rcon-setup enables RCON" {
    skip "Requires rcon-setup.sh"
}

@test "rcon-client sends commands" {
    skip "Requires rcon-client.sh and running server"
}

@test "rcon-client test connection works" {
    skip "Requires rcon-client.sh and running server"
}

