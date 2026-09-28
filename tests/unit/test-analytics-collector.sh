#!/usr/bin/env bats
# Unit Tests: analytics-collector.sh
# Tests for the analytics data collector script

load '../helpers/bats-support/load'
load '../helpers/bats-assert/load'

setup() {
    # bats copies the test file into a temp location, so BASH_SOURCE is not a
    # reliable way to find the repo; BATS_TEST_DIRNAME points at the real file.
    REPO_DIR="$(cd "$BATS_TEST_DIRNAME/../.." && pwd)"

    # analytics-collector.sh and analytics-processor.py resolve their output
    # directory from their own location, so running a copy of scripts/ inside a
    # temp directory keeps every write out of the working tree.
    TEST_DIR="$(mktemp -d)"
    cp -R "$REPO_DIR/scripts" "$TEST_DIR/scripts"
    cd "$TEST_DIR" || exit 1

    mkdir -p analytics

    # A stub docker. The container is stopped unless a test writes
    # $STATE_DIR/running; the outputs below are what a Pi reports.
    STATE_DIR="$TEST_DIR/state"
    mkdir -p bin "$STATE_DIR"
    cat > bin/docker <<STUB
#!/bin/bash
case "\$1" in
    ps)
        [ -f "$STATE_DIR/running" ] && echo "abc123 minecraft-server Up 2 hours"
        ;;
    logs)
        echo "[12:00:00] [Server thread/INFO]: alice joined the game"
        echo "[12:01:00] [Server thread/INFO]: TPS: 19.85"
        echo "[12:02:00] [Server thread/INFO]: bob left the game"
        ;;
    stats)
        case "\$*" in
            *CPUPerc*) echo "12.50%" ;;
            *MemUsage*) cat "$STATE_DIR/memusage" ;;
            *NetIO*) echo "1.2MB / 500kB" ;;
        esac
        ;;
    exec)
        echo "There are 2 of a max of 10 players online: alice, bob"
        ;;
esac
exit 0
STUB
    chmod +x bin/docker
    echo "1024.5MiB / 3.8GiB" > "$STATE_DIR/memusage"
    export PATH="$TEST_DIR/bin:$PATH"
}

# Prints the named fields of the latest performance record, space separated
performance_fields() {
    python3 -c 'import json, sys; d = json.loads(open("analytics/performance.jsonl").readlines()[-1])["data"]; print(*(d[k] for k in sys.argv[1:]))' "$@"
}

# Every line of every file the collector wrote must be a JSON object carrying
# a numeric timestamp, a datetime and a data payload.
assert_valid_analytics() {
    local files=(analytics/*.jsonl)
    [ -f "${files[0]}" ] || { echo "no .jsonl files written"; return 1; }
    run python3 - "${files[@]}" <<'PY'
import json, sys
for path in sys.argv[1:]:
    with open(path) as f:
        for number, line in enumerate(f, 1):
            try:
                record = json.loads(line)
            except ValueError as exc:
                sys.exit(f"{path}:{number}: not JSON ({exc}): {line.strip()}")
            for key in ("timestamp", "datetime", "data"):
                if key not in record:
                    sys.exit(f"{path}:{number}: missing {key}")
            if not isinstance(record["timestamp"], (int, float)):
                sys.exit(f"{path}:{number}: timestamp is not numeric")
PY
    assert_success
}

teardown() {
    cd /
    rm -rf "$TEST_DIR"
}

@test "analytics-collector.sh creates analytics directory" {
    # Remove directory if it exists
    rm -rf analytics

    # Run script
    run ./scripts/analytics-collector.sh

    # Check that directory was created
    assert_file_exists analytics
}

@test "analytics-collector.sh writes one JSONL file per metric" {
    touch "$STATE_DIR/running"

    run ./scripts/analytics-collector.sh
    assert_success

    for metric in players player_events performance network world_stats; do
        assert_file_exists "analytics/${metric}.jsonl"
    done
}

@test "analytics-collector.sh records zeros when the server is stopped" {
    run ./scripts/analytics-collector.sh
    assert_success
    assert_valid_analytics

    run grep -c '"tps":0,' analytics/performance.jsonl
    assert_output "1"
}

@test "analytics-collector.sh writes valid JSON while the server is running" {
    touch "$STATE_DIR/running"

    run ./scripts/analytics-collector.sh
    assert_success
    assert_valid_analytics
}

@test "analytics-collector.sh parses docker stats and logs" {
    touch "$STATE_DIR/running"

    run ./scripts/analytics-collector.sh
    assert_success

    run performance_fields tps cpu memory
    assert_output "19.85 12.5 1024.5"
}

@test "analytics-collector.sh reads whole-number and GiB memory" {
    touch "$STATE_DIR/running"

    # The old pattern needed a decimal point, so "512MiB" left memory empty
    echo "512MiB / 3.8GiB" > "$STATE_DIR/memusage"
    run ./scripts/analytics-collector.sh
    assert_success
    run performance_fields memory
    assert_output "512"

    echo "1.5GiB / 3.8GiB" > "$STATE_DIR/memusage"
    run ./scripts/analytics-collector.sh
    assert_success
    run performance_fields memory
    assert_output "1536.0"
    assert_valid_analytics
}

@test "analytics-collector.sh counts join and leave events" {
    touch "$STATE_DIR/running"

    run ./scripts/analytics-collector.sh
    assert_success

    run cat analytics/player_events.jsonl
    assert_line '"data":\[{"type":"join","count":1},{"type":"leave","count":1}\]'
}
