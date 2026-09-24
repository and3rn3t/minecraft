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
    #   ps               - non-empty while the container is running
    #   container-image  - the image id the running container was started from
    #   image            - the image id the service's tag points at
    #   new-image        - if present, what a pull moves the tag to
    #   compose-config   - what `docker compose config` prints
    #   players          - how many players the status ping reports
    STATE_DIR="$TEST_DIR/state"
    mkdir -p bin "$STATE_DIR"
    echo "running" > "$STATE_DIR/ps"
    echo "image-a" > "$STATE_DIR/container-image"
    echo "image-a" > "$STATE_DIR/image"
    printf 'services:\n  minecraft:\n    image: ghcr.io/example/minecraft-server:latest\n' > "$STATE_DIR/compose-config"
    echo "0" > "$STATE_DIR/players"
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
    *"config --images"*)
        echo "ghcr.io/example/minecraft-server:latest"
        ;;
    *"compose config"*)
        cat "$STATE_DIR/compose-config"
        ;;
    "image inspect"*)
        cat "$STATE_DIR/image"
        ;;
    "inspect"*)
        cat "$STATE_DIR/container-image"
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
    export PLAYER_COUNT_CMD="cat $STATE_DIR/players"
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

@test "run addresses the compose service, not the container name" {
    # The service is `minecraft`; `minecraft-server` is the container. Passing
    # the container name to compose matched no service, so the script decided
    # the server was stopped on every run and never updated anything.
    run scripts/auto-update.sh run
    assert_success
    assert_docker_called_with "pull minecraft"
    assert_docker_not_called_with "^compose .* minecraft-server$"
}

@test "run waits while anyone is online" {
    echo "image-b" > "$STATE_DIR/new-image"
    echo "2" > "$STATE_DIR/players"

    run scripts/auto-update.sh run
    assert_success
    assert_line "2 player(s) online"
    assert_docker_not_called_with "up -d"
}

@test "run waits when it cannot tell who is online" {
    echo "image-b" > "$STATE_DIR/new-image"
    export PLAYER_COUNT_CMD="false"

    run scripts/auto-update.sh run
    assert_success
    assert_line "did not say who is online"
    assert_docker_not_called_with "up -d"
}

@test "run applies a deferred update once the server is empty" {
    # A previous run pulled image-b but someone was playing. Nothing new is
    # pulled this time; the container is still behind its tag, so restart.
    echo "image-b" > "$STATE_DIR/image"

    run scripts/auto-update.sh run
    assert_success
    assert_line "New image found"
    assert_docker_called_with "up -d"
}

@test "run does not pull an image that is built locally" {
    printf 'services:\n  minecraft:\n    build:\n      context: .\n' > "$STATE_DIR/compose-config"

    run scripts/auto-update.sh run
    assert_success
    assert_docker_not_called_with "pull"
}

@test "run restarts onto a locally rebuilt image" {
    printf 'services:\n  minecraft:\n    build:\n      context: .\n' > "$STATE_DIR/compose-config"
    echo "image-b" > "$STATE_DIR/image"

    run scripts/auto-update.sh run
    assert_success
    assert_docker_called_with "up -d"
}
