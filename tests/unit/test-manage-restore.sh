#!/usr/bin/env bats
# Unit Tests: manage.sh restore (and the failure path of manage.sh backup)
#
# docker is stubbed on PATH (compose is scripts/lib/common.sh's wrapper around
# it); calls are logged to $STATE_DIR/calls. The confirmation prompt reads
# from stdin, so tests pipe "y" or "n" into `manage.sh restore` via `bash -c`.

bats_require_minimum_version 1.5.0

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

    # log-line defaults to a clean startup; tests override it to simulate a
    # failed or a silent world load.
    echo '[Server thread/INFO]: Done (10.5s)! For help, type "help"' > "$STATE_DIR/log-line"

    cat > bin/docker <<STUB
#!/bin/bash
echo "docker \$*" >> "$STATE_DIR/calls"
case "\$*" in
    "compose version") echo "Docker Compose version v2.0.0" ;;
    # The archive step: tar runs in a throwaway container. A test makes it fail by creating tar-fails
    "compose run"*)
        # tar-junk: exit 0 but write something that is not a tar stream, so the archive step "works"
        # and only the integrity check can tell. It has to be at least a full 512-byte block:
        # GNU tar lists a shorter stream as an empty archive and exits 0, where BSD tar rejects it.
        if [ -f "$STATE_DIR/tar-junk" ]; then head -c 1024 /dev/zero | tr '\0' 'x'; exit 0; fi
        if [ -f "$STATE_DIR/tar-fails" ]; then
            echo "tar: ./world/playerdata/steve.dat: Cannot open: Permission denied" >&2
            echo "tar: Exiting with failure status due to previous errors" >&2
            exit 2
        fi
        ;;
    ps) [ -f "$STATE_DIR/running" ] && echo "abc123 minecraft-server Up" ;;
    "ps --format {{.Names}}") [ -f "$STATE_DIR/running" ] && echo "minecraft-server" ;;
    "compose logs -f minecraft") cat "$STATE_DIR/log-line" ;;
esac
exit 0
STUB
    chmod +x bin/docker
    # scripts/lib/common.sh takes its update lock with util-linux flock, which
    # macOS lacks. The shim takes a real lock, so the contention test still means
    # something; on Linux the real flock is used.
    command -v flock >/dev/null 2>&1 || cp "$REPO_DIR/tests/helpers/flock" "$TEST_DIR/bin/flock"
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

@test "restore refuses to run while a deploy holds the update lock" {
    mkdir -p .deploy
    exec 8>.deploy/lock
    flock -n 8

    restore_confirmed backups/good.tar.gz
    exec 8>&-
    assert_failure
    assert_line "A deploy or update is running"
    assert_not_called "compose down"
    assert_not_called "compose up"
}

@test "restore fails when the log shows the world failed to load" {
    echo '[Server thread/ERROR]: Exception in server tick loop' > "$STATE_DIR/log-line"

    restore_confirmed backups/good.tar.gz
    assert_failure
    assert_line "World failed to load"
}

@test "restore fails when no load confirmation appears in the logs" {
    : > "$STATE_DIR/log-line"

    restore_confirmed backups/good.tar.gz
    assert_failure
    assert_line "No clean-load confirmation"
}

# Substring checks that fail the test on every bash. A bare `[[ ... ]]` that is not the last
# command does not abort a Bats test on bash 3.2 (macOS), so a wrong assertion would pass.
stderr_has() { [[ "$stderr" == *"$1"* ]] || { echo "expected stderr to contain: $1"; echo "stderr: $stderr"; return 1; }; }
stdout_lacks() { [[ "$output" != *"$1"* ]] || { echo "expected stdout NOT to contain: $1"; echo "stdout: $output"; return 1; }; }

@test "a failed backup says why on stderr, which is all POST /api/backup returns" {
    mkdir -p data
    echo "level" > data/level.dat
    touch "$STATE_DIR/tar-fails"

    run --separate-stderr scripts/manage.sh backup

    assert_failure
    stderr_has "Backup creation failed"
    stderr_has "Permission denied"
    # Nothing about the failure on stdout, where the API would never see it
    stdout_lacks "Backup creation failed"
    stdout_lacks "Permission denied"
    # and no half-written archive is left behind
    run bash -c "ls backups | grep -c '^minecraft_backup_' || true"
    [ "$output" = "0" ]
}

@test "a backup without a data directory says so on stderr" {
    # no ./data in this test directory
    run --separate-stderr scripts/manage.sh backup

    assert_failure
    stderr_has "No data directory found"
    stdout_lacks "No data directory found"
}

@test "an archive that fails the integrity check is reported on stderr and removed" {
    mkdir -p data
    echo "level" > data/level.dat
    touch "$STATE_DIR/tar-junk"

    run --separate-stderr scripts/manage.sh backup

    assert_failure
    stderr_has "Backup verification failed"
    stdout_lacks "Backup verification failed"
    # the unreadable archive is not left behind to be offered as a backup
    run bash -c "ls backups | grep -c '^minecraft_backup_' || true"
    [ "$output" = "0" ]
}
