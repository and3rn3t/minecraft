#!/usr/bin/env bats
# Unit Tests: ban-manager.sh
#
# ban-manager.sh sources rcon-client.sh to reach RCON (see scripts/ban-manager.sh);
# docker is stubbed on PATH to simulate the container being present or absent,
# and rcon-cli's availability and success inside it. Calls are logged to
# $STATE_DIR/calls.

load '../helpers/bats-support/load'
load '../helpers/bats-assert/load'

setup() {
    REPO_DIR="$(cd "$BATS_TEST_DIRNAME/../.." && pwd)"
    TEST_DIR="$(mktemp -d)"
    cp -R "$REPO_DIR/scripts" "$TEST_DIR/scripts"
    mkdir -p "$TEST_DIR/data" "$TEST_DIR/bin"
    cd "$TEST_DIR" || exit 1

    STATE_DIR="$TEST_DIR/state"
    mkdir -p "$STATE_DIR"
    : > "$STATE_DIR/calls"

    # By default: container running, rcon-cli present in it, and RCON calls
    # succeed. Tests override these files to exercise the other paths.
    touch "$STATE_DIR/running"
    touch "$STATE_DIR/rcon-cli-present"

    cat > bin/docker <<STUB
#!/bin/bash
echo "docker \$*" >> "$STATE_DIR/calls"
case "\$1" in
    ps)
        [ -f "$STATE_DIR/running" ] && echo "minecraft-server"
        ;;
    exec)
        case "\$*" in
            *"command -v rcon-cli"*)
                [ -f "$STATE_DIR/rcon-cli-present" ] && exit 0
                exit 1
                ;;
            *"rcon-cli"*)
                if [ -f "$STATE_DIR/rcon-fails" ]; then
                    echo "Failed to connect" >&2
                    exit 1
                fi
                echo "ok"
                ;;
        esac
        ;;
esac
exit 0
STUB
    chmod +x bin/docker
    export PATH="$TEST_DIR/bin:$PATH"
    export BANNED_PLAYERS_FILE="$TEST_DIR/data/banned-players.json"
    export BANNED_IPS_FILE="$TEST_DIR/data/banned-ips.json"

    # rcon-client.sh (sourced by ban-manager.sh) refuses to send a command
    # without a configured password; give it one via the same config file a
    # real deployment would use.
    mkdir -p "$TEST_DIR/config"
    cat > "$TEST_DIR/config/rcon.conf" <<CONF
RCON_HOST=localhost
RCON_PORT=25575
RCON_PASSWORD=test-password
CONF
}

teardown() {
    rm -rf "$TEST_DIR"
}

@test "ban-manager ban adds the player to banned-players.json" {
    run bash scripts/ban-manager.sh ban Griefer42 "Griefing"
    assert_success
    assert_line "Player banned: Griefer42"

    run cat "$BANNED_PLAYERS_FILE"
    assert_line '"name": "Griefer42"'
    assert_line '"reason": "Griefing"'
}

@test "ban-manager ban notifies the live server over RCON when it is reachable" {
    run bash scripts/ban-manager.sh ban Griefer42 "Griefing"
    assert_success

    run cat "$STATE_DIR/calls"
    assert_line "docker exec minecraft-server rcon-cli -H localhost -p 25575 -P test-password ban Griefer42 Griefing"
}

@test "ban-manager ban still succeeds when the container is not running" {
    rm -f "$STATE_DIR/running"
    run bash scripts/ban-manager.sh ban Griefer42 "Griefing"
    assert_success
    assert_line "Player banned: Griefer42"

    run grep -q "exec" "$STATE_DIR/calls"
    assert_failure
}

@test "ban-manager ban still succeeds when rcon-cli is not installed in the container" {
    rm -f "$STATE_DIR/rcon-cli-present"
    run bash scripts/ban-manager.sh ban Griefer42 "Griefing"
    assert_success
    assert_line "Player banned: Griefer42"
}

@test "ban-manager ban still succeeds when the RCON call itself fails" {
    touch "$STATE_DIR/rcon-fails"
    run bash scripts/ban-manager.sh ban Griefer42 "Griefing"
    assert_success
    assert_line "Player banned: Griefer42"

    run cat "$BANNED_PLAYERS_FILE"
    assert_line '"name": "Griefer42"'
}

@test "ban-manager unban removes the player and notifies over RCON" {
    bash scripts/ban-manager.sh ban Griefer42 "Griefing" >/dev/null
    : > "$STATE_DIR/calls"

    run bash scripts/ban-manager.sh unban Griefer42
    assert_success
    assert_line "Player unbanned: Griefer42"

    run grep -q "Griefer42" "$BANNED_PLAYERS_FILE"
    assert_failure

    run cat "$STATE_DIR/calls"
    assert_line "docker exec minecraft-server rcon-cli -H localhost -p 25575 -P test-password pardon Griefer42"
}

@test "ban-manager ban-ip and unban-ip notify over RCON the same way" {
    run bash scripts/ban-manager.sh ban-ip 192.168.1.100 "Suspicious"
    assert_success
    assert_line "IP address banned: 192.168.1.100"

    run cat "$STATE_DIR/calls"
    assert_line "docker exec minecraft-server rcon-cli -H localhost -p 25575 -P test-password ban-ip 192.168.1.100"

    : > "$STATE_DIR/calls"
    run bash scripts/ban-manager.sh unban-ip 192.168.1.100
    assert_success
    assert_line "IP address unbanned: 192.168.1.100"

    run cat "$STATE_DIR/calls"
    assert_line "docker exec minecraft-server rcon-cli -H localhost -p 25575 -P test-password pardon-ip 192.168.1.100"
}
