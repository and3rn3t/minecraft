#!/usr/bin/env bats
# Unit Tests: manage.sh restore
#
# docker is stubbed on PATH (compose is scripts/lib/common.sh's wrapper around
# it); calls are logged to $STATE_DIR/calls. The confirmation prompt reads
# from stdin, so tests pipe "y" or "n" into `manage.sh restore` via `bash -c`.

load '../helpers/bats-support/load'
load '../helpers/bats-assert/load'

setup() {
    REPO_DIR="$(cd "$BATS_TEST_DIRNAME/../.." && pwd)"
    TEST_DIR="$(mktemp -d)"
    cp -R "$REPO_DIR/scripts" "$TEST_DIR/scripts"
    mkdir -p "$TEST_DIR/backups" "$TEST_DIR/bin"
    cd "$TEST_DIR" || exit 1

    STATE_DIR="$TEST_DIR/state"
    mkdir -p "$STATE_DIR"
    : > "$STATE_DIR/calls"

    cat > bin/docker <<STUB
#!/bin/bash
echo "docker \$*" >> "$STATE_DIR/calls"
case "\$*" in
    "compose version") echo "Docker Compose version v2.0.0" ;;
    ps) [ -f "$STATE_DIR/running" ] && echo "abc123 minecraft-server Up" ;;
    "compose logs -f minecraft") echo '[Server thread/INFO]: Done (10.5s)! For help, type "help"' ;;
esac
exit 0
STUB
    chmod +x bin/docker
    export PATH="$TEST_DIR/bin:$PATH"

    # A good backup: a tar.gz of a single marker file, restore's expected input
    mkdir -p seed
    echo "restored" > seed/marker.txt
    tar -czf backups/good.tar.gz -C seed .

    echo "not a tarball" > backups/corrupt.tar.gz
}

teardown() {
    cd /
    rm -rf "$TEST_DIR"
}

assert_called() {
    grep -q -- "$1" "$STATE_DIR/calls" || { echo "Expected a call matching: $1"; return 1; }
}

assert_not_called() {
    if grep -q -- "$1" "$STATE_DIR/calls"; then
        echo "Expected no call matching: $1"
        return 1
    fi
}

restore_confirmed() {
    run bash -c "echo y | scripts/manage.sh restore '$1'"
}

restore_declined() {
    run bash -c "echo n | scripts/manage.sh restore '$1'"
}

@test "restore without a backup file prints usage and exits nonzero" {
    run scripts/manage.sh restore
    assert_failure
    assert_line "Usage:"
}

@test "restore fails when the named backup does not exist" {
    run bash -c "echo y | scripts/manage.sh restore backups/does-not-exist.tar.gz"
    assert_failure
    assert_line "Backup not found"
}

@test "restore does nothing when the confirmation prompt is declined" {
    mkdir -p data
    echo "original" > data/marker.txt

    restore_declined backups/good.tar.gz
    assert_success
    assert_line "Cancelled"
    [ "$(cat data/marker.txt)" = "original" ]
    assert_not_called "compose down"
    assert_not_called "compose up"
}

@test "restore moves existing data aside instead of deleting it" {
    mkdir -p data
    echo "original" > data/marker.txt

    restore_confirmed backups/good.tar.gz
    assert_success
    [ "$(cat data/marker.txt)" = "restored" ]

    local aside
    aside="$(ls -d data.pre-restore.* 2>/dev/null | head -1)"
    [ -n "$aside" ]
    [ "$(cat "$aside/marker.txt")" = "original" ]
}

@test "restore starts the server after a successful extraction" {
    restore_confirmed backups/good.tar.gz
    assert_success
    assert_called "compose up -d"
    assert_line "Done ("
}

@test "restore stops a running server before touching data" {
    touch "$STATE_DIR/running"
    restore_confirmed backups/good.tar.gz
    assert_success
    assert_called "compose down"
}

@test "restore does not stop the server when it is not running" {
    restore_confirmed backups/good.tar.gz
    assert_success
    assert_not_called "compose down"
}

@test "restore rolls back automatically when the archive is corrupt" {
    mkdir -p data
    echo "original" > data/marker.txt

    restore_confirmed backups/corrupt.tar.gz
    assert_failure
    assert_line "Extraction failed"
    [ "$(cat data/marker.txt)" = "original" ]
    # The failed extraction's empty ./data was cleaned up, and nothing was
    # left behind under a data.pre-restore.* name either
    run bash -c 'ls -d data.pre-restore.* 2>/dev/null'
    assert_output ""
}

@test "restore accepts a bare filename resolved against ./backups" {
    restore_confirmed good.tar.gz
    assert_success
    [ "$(cat data/marker.txt)" = "restored" ]
}
