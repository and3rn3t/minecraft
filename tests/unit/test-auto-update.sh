#!/usr/bin/env bats
# Unit Tests: auto-update.sh
#
# The unit this replaces ran `docker compose up -d --force-recreate` every hour
# regardless of whether a new image existed, so these tests are mostly about
# what the script declines to do.
#
# tests/helpers/bats-assert is a minimal stub: assert_output matches exactly and
# assert_line greps, with no refute helpers. Negative checks are therefore
# written as an explicit grep whose failure is asserted.

load '../helpers/bats-support/load'
load '../helpers/bats-assert/load'

setup() {
    REPO_DIR="$(cd "$BATS_TEST_DIRNAME/../.." && pwd)"

    TEST_DIR="$(mktemp -d)"
    cp -R "$REPO_DIR/scripts" "$TEST_DIR/scripts"
    cd "$TEST_DIR" || exit 1

    # A stub docker whose behaviour each test controls through these files.
    STATE_DIR="$TEST_DIR/state"
    mkdir -p bin "$STATE_DIR"
    echo "running" > "$STATE_DIR/ps"
    echo "image-a" > "$STATE_DIR/image"
    : > "$STATE_DIR/calls"

    cat > bin/docker <<STUB
#!/bin/bash
echo "\$@" >> "$STATE_DIR/calls"
case "\$*" in
    "compose version")
        echo "Docker Compose version v2.0.0"
        ;;
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

# Helper: assert the stub was never asked to do something
assert_docker_not_called_with() {
    run grep -q -- "$1" "$STATE_DIR/calls"
    assert_failure
}

# Helper: assert the stub was asked to do something
assert_docker_called_with() {
    run grep -q -- "$1" "$STATE_DIR/calls"
    assert_success
}

@test "auto-update.sh shows usage without a subcommand" {
    run scripts/auto-update.sh
    assert_failure
    assert_line "Usage:"
}

@test "auto-update.sh rejects an unknown subcommand" {
    run scripts/auto-update.sh frobnicate
    assert_failure
    assert_line "Usage:"
}

@test "run does not restart when the image is unchanged" {
    run scripts/auto-update.sh run
    assert_success
    assert_line "Already up to date"
    assert_docker_not_called_with "up -d"
}

@test "run restarts when the image changed" {
    echo "image-b" > "$STATE_DIR/new-image"

    run scripts/auto-update.sh run
    assert_success
    assert_line "New image found"
    assert_docker_called_with "up -d"
}

@test "run leaves a stopped server stopped" {
    # A stopped server was stopped for a reason; starting it behind the owner's
    # back would undo bedtime or a deliberate maintenance shutdown.
    : > "$STATE_DIR/ps"

    run scripts/auto-update.sh run
    assert_success
    assert_line "not running"
    assert_docker_not_called_with "up -d"
}

@test "run does not pull when the server is stopped" {
    : > "$STATE_DIR/ps"

    run scripts/auto-update.sh run
    assert_success
    assert_docker_not_called_with "pull"
}

@test "run still restarts a changed image only once" {
    echo "image-b" > "$STATE_DIR/new-image"
    run scripts/auto-update.sh run
    assert_success

    run bash -c "grep -c -- 'up -d' '$STATE_DIR/calls'"
    assert_output "1"
}

@test "check reports when up to date" {
    run scripts/auto-update.sh check
    assert_success
    assert_line "Up to date"
}

@test "check reports an available update" {
    echo "image-b" > "$STATE_DIR/new-image"

    run scripts/auto-update.sh check
    assert_success
    assert_line "update is available"
}

@test "check never restarts the server" {
    echo "image-b" > "$STATE_DIR/new-image"

    run scripts/auto-update.sh check
    assert_success
    assert_docker_not_called_with "up -d"
}
