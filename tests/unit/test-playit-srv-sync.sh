#!/usr/bin/env bats
# Unit Tests: playit-srv-sync.sh
#
# curl is a stub. It answers DNS-over-HTTPS lookups from $STATE_DIR/doh.json,
# Cloudflare record reads from $STATE_DIR/cf-get.json and record updates from
# $STATE_DIR/cf-patch.json, and logs every call's arguments to
# $STATE_DIR/calls. A missing file makes that call fail, like a network error.
#
# tests/helpers/bats-assert is a minimal stub: assert_output matches exactly,
# assert_line greps and assert_failure ignores an exit code, with no refute
# helpers. Exit codes are checked explicitly, and negative checks are
# written as an explicit grep whose failure is asserted.

load '../helpers/bats-support/load'
load '../helpers/bats-assert/load'

setup() {
    REPO_DIR="$(cd "$BATS_TEST_DIRNAME/../.." && pwd)"
    TEST_DIR="$(mktemp -d)"
    STATE_DIR="$TEST_DIR/state"
    mkdir -p "$STATE_DIR" "$TEST_DIR/bin"
    : > "$STATE_DIR/calls"
    export STATE_DIR

    cat > "$TEST_DIR/bin/curl" <<'EOF'
#!/bin/bash
echo "$*" >> "$STATE_DIR/calls"
case "$*" in
    *dns-query*)   f="$STATE_DIR/doh.json" ;;
    *"-X PATCH"*)  f="$STATE_DIR/cf-patch.json" ;;
    *dns_records*) f="$STATE_DIR/cf-get.json" ;;
    *)             exit 7 ;;
esac
[ -f "$f" ] || exit 7
cat "$f"
EOF
    chmod +x "$TEST_DIR/bin/curl"
    export PATH="$TEST_DIR/bin:$PATH"

    cat > "$TEST_DIR/playit.conf" <<'EOF'
PLAYIT_HOST=della-bd.tun.ply.gg
GAME_SRV_NAME=_minecraft._tcp.mine.example.com
CLOUDFLARE_API_TOKEN=test-token
CLOUDFLARE_ZONE_ID=zone123
EOF
    export PLAYIT_CONFIG="$TEST_DIR/playit.conf"

    SCRIPT="$REPO_DIR/scripts/playit-srv-sync.sh"
}

teardown() {
    rm -rf "$TEST_DIR"
}

# playit's own record: "priority weight port target"
playit_says() {
    printf '{"Status":0,"Answer":[{"name":"_minecraft._tcp.della-bd.tun.ply.gg","type":33,"TTL":300,"data":"%s"}]}' \
        "$1" > "$STATE_DIR/doh.json"
}

# The Cloudflare record's port and target
cloudflare_has() {
    printf '{"success":true,"errors":[],"result":[{"id":"rec1","type":"SRV","data":{"priority":0,"weight":5,"port":%s,"target":"%s"}}]}' \
        "$1" "$2" > "$STATE_DIR/cf-get.json"
}

patched() {
    grep -q -- "-X PATCH" "$STATE_DIR/calls"
}

@test "check reports in sync and exits 0 when the records match" {
    playit_says "1 1 33903 della-bd.tun.ply.gg"
    cloudflare_has 33903 della-bd.tun.ply.gg
    run "$SCRIPT" check
    assert_success
    assert_line "In sync"
}

@test "target comparison ignores the trailing dot and case" {
    playit_says "1 1 33903 Della-BD.tun.ply.gg."
    cloudflare_has 33903 della-bd.tun.ply.gg.
    run "$SCRIPT" check
    assert_success
}

@test "check exits 1 on drift and writes nothing" {
    playit_says "1 1 33903 della-bd.tun.ply.gg"
    cloudflare_has 33856 della-bd.tun.ply.gg
    run "$SCRIPT" check
    assert_failure
    [ "$status" -eq 1 ]
    assert_line "Out of sync"
    run patched
    assert_failure
}

@test "sync updates the port, keeping Cloudflare's priority and weight" {
    playit_says "1 1 33903 della-bd.tun.ply.gg"
    cloudflare_has 33856 della-bd.tun.ply.gg
    echo '{"success":true}' > "$STATE_DIR/cf-patch.json"
    run "$SCRIPT" sync
    assert_success
    assert_line "Updated"
    run grep -- "-X PATCH" "$STATE_DIR/calls"
    assert_line '"priority":0,"weight":5,"port":33903,"target":"della-bd.tun.ply.gg"'
    assert_line "dns_records/rec1"
}

@test "sync does nothing when already in sync" {
    playit_says "1 1 33903 della-bd.tun.ply.gg"
    cloudflare_has 33903 della-bd.tun.ply.gg
    run "$SCRIPT" sync
    assert_success
    run patched
    assert_failure
}

@test "sync fails when Cloudflare rejects the update" {
    playit_says "1 1 33903 della-bd.tun.ply.gg"
    cloudflare_has 33856 della-bd.tun.ply.gg
    echo '{"success":false,"errors":[{"code":9109}]}' > "$STATE_DIR/cf-patch.json"
    run "$SCRIPT" sync
    assert_failure
    [ "$status" -eq 1 ]
    assert_line "update failed"
}

@test "a failed DNS lookup changes nothing" {
    cloudflare_has 33856 della-bd.tun.ply.gg
    run "$SCRIPT" sync
    assert_failure
    [ "$status" -eq 1 ]
    assert_line "Could not read playit"
    run patched
    assert_failure
}

@test "an SRV answer for a different host is refused" {
    playit_says "1 1 25565 attacker.example.net"
    cloudflare_has 33903 della-bd.tun.ply.gg
    run "$SCRIPT" sync
    assert_failure
    [ "$status" -eq 1 ]
    run patched
    assert_failure
}

@test "an answer with no SRV record is refused" {
    echo '{"Status":3}' > "$STATE_DIR/doh.json"
    cloudflare_has 33903 della-bd.tun.ply.gg
    run "$SCRIPT" sync
    assert_failure
    [ "$status" -eq 1 ]
    run patched
    assert_failure
}

@test "a port outside 1-65535 is refused" {
    playit_says "1 1 70000 della-bd.tun.ply.gg"
    cloudflare_has 33903 della-bd.tun.ply.gg
    run "$SCRIPT" sync
    assert_failure
    [ "$status" -eq 1 ]
    run patched
    assert_failure
}

@test "a missing Cloudflare record changes nothing" {
    playit_says "1 1 33903 della-bd.tun.ply.gg"
    echo '{"success":true,"errors":[],"result":[]}' > "$STATE_DIR/cf-get.json"
    run "$SCRIPT" sync
    assert_failure
    [ "$status" -eq 1 ]
    assert_line "Could not read the Cloudflare"
    run patched
    assert_failure
}

@test "missing settings are named and exit 2" {
    echo "PLAYIT_HOST=della-bd.tun.ply.gg" > "$PLAYIT_CONFIG"
    run "$SCRIPT" check
    assert_failure
    [ "$status" -eq 2 ]
    assert_line "GAME_SRV_NAME CLOUDFLARE_API_TOKEN CLOUDFLARE_ZONE_ID"
}

@test "a missing config file exits 2" {
    rm "$PLAYIT_CONFIG"
    run "$SCRIPT" check
    assert_failure
    [ "$status" -eq 2 ]
    assert_line "Config not found"
}

@test "an unknown command prints usage and exits 2" {
    run "$SCRIPT" frobnicate
    assert_failure
    [ "$status" -eq 2 ]
    assert_line "Usage:"
}
