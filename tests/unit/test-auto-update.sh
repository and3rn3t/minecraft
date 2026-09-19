#!/usr/bin/env bats
# Unit Tests: auto-update.sh
#
# The unit this replaces ran `docker compose up -d --force-recreate` every hour
# regardless of whether a new image existed, so these tests are mostly about
# what the script declines to do.

load '../helpers/bats-support/load'
load '../helpers/bats-assert/load'

setup() {
    REPO_DIR="$(cd "$BATS_TEST_DIRNAME/../.." && pwd)"

    TEST_DIR="$(mktemp -d)"
    cp -R "$REPO_DIR/scripts" "$TEST_DIR/scripts"
    cd "$TEST_DIR" || exit 1

    # A stub docker whose behaviour each test controls through these files.
    mkdir -p bin
    STATE_DIR="$TEST_DIR/state"
    mkdir -p "$STATE_DIR"
    echo "running" > "$STATE_DIR/ps"
    echo "image-a" > "$STATE_DIR/image"
    : > "$STATE_DIR/calls"

    cat > bin/docker <<STUB
#!/bin/bash
echo "\$@" >> "$STATE_DIR/calls"
case "\$*" in
    *"ps --status running"*)
        cat "$STATE_DIR/ps"
        ;;
    *"images -q"*)
        cat "$STATE_DIR/image"
        ;;
    *pull*)
        if [ -f "$STATE_DIR/new-image" ]; then
            cat "$STATE_DIR/new-image" > "$STATE_DIR/image"
        fi
        echo "pulled"
        ;;
    *)
        echo "ok"
        ;;
esac
exit 0
STUB
    chmod +x bin/docker
    export PATH="$TEST_DIR/bin:$PATH"
}

teardown() {
    cd /
    rm -rf "$TEST_DIR"
}

@test "auto-update.sh passes shellcheck-able syntax" {
    run bash -n scripts/auto-update.sh
    assert_success
}

@test "auto-update.sh shows usage without a subcommand" {
    run scripts/auto-update.sh
    assert_failure
    assert_output --partial "Usage:"
}

@test "auto-update.sh rejects an unknown subcommand" {
    run scripts/auto-update.sh frobnicate
    assert_failure
    assert_output --partial "Usage:"
}

@test "run does not restart when the image is unchanged" {
    run scripts/auto-update.sh run
    assert_success
    assert_output --partial "Already up to date"
    refute_line --partial "up -d"
}

@test "run restarts when the image changed" {
    echo "image-b" > "$STATE_DIR/new-image"

    run scripts/auto-update.sh run
    assert_success
    assert_output --partial "New image found"

    run grep -c "up -d" "$STATE_DIR/calls"
    assert_success
}

@test "run leaves a stopped server stopped" {
    # A stopped server was stopped for a reason; starting it behind the owner's
    # back would undo bedtime or a deliberate maintenance shutdown.
    : > "$STATE_DIR/ps"

    run scripts/auto-update.sh run
    assert_success
    assert_output --partial "not running"

    run grep -q "up -d" "$STATE_DIR/calls"
    assert_failure
}

@test "run does not pull when the server is stopped" {
    : > "$STATE_DIR/ps"

    run scripts/auto-update.sh run
    assert_success

    run grep -q "pull" "$STATE_DIR/calls"
    assert_failure
}

@test "check reports when up to date" {
    run scripts/auto-update.sh check
    assert_success
    assert_output --partial "Up to date"
}

@test "check reports an available update" {
    echo "image-b" > "$STATE_DIR/new-image"

    run scripts/auto-update.sh check
    assert_success
    assert_output --partial "update is available"
}

@test "check never restarts the server" {
    echo "image-b" > "$STATE_DIR/new-image"

    run scripts/auto-update.sh check
    assert_success

    run grep -q "up -d" "$STATE_DIR/calls"
    assert_failure
}
