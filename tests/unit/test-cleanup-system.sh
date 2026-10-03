#!/usr/bin/env bats
# Unit Tests: cleanup-system.sh
#
# The script is a manual clean-up that deletes things, so these tests are mostly
# about what it must NOT touch: backups (pruned by the retention policy, not here),
# other programs' files in /tmp, and Docker images or volumes that are in use or
# unused-but-valuable. sudo, apt-get and docker are stubbed, and HOME is a
# throwaway directory.

load '../helpers/bats-support/load'
load '../helpers/bats-assert/load'

setup() {
    # The real rm, found before PATH is changed below. The stub rm that setup puts
    # first in PATH refuses /tmp, so anything that must really delete (the stub's
    # pass-through and teardown) uses this path, not "rm" and not `command rm`
    # (which still searches PATH).
    REAL_RM="$(command -v rm)"
    REPO_DIR="$(cd "$BATS_TEST_DIRNAME/../.." && pwd)"
    TEST_DIR="$(mktemp -d)"
    cp -R "$REPO_DIR/scripts" "$TEST_DIR/scripts"
    mkdir -p "$TEST_DIR/bin" "$TEST_DIR/state" "$TEST_DIR/home" \
        "$TEST_DIR/backups" "$TEST_DIR/data/logs" "$TEST_DIR/logs"
    cd "$TEST_DIR" || exit 1

    # docker: record every call; fail the prune commands while state/prune-fails exists
    cat > bin/docker <<STUB
#!/bin/bash
echo "docker \$*" >> "$TEST_DIR/state/docker-calls"
case "\$*" in
    *prune*) [ -f "$TEST_DIR/state/prune-fails" ] && exit 1 ;;
esac
exit 0
STUB
    # sudo only ever runs apt-get (itself a stub), so a script that tried to sudo
    # anything else would fail here instead of running on the real machine
    printf '#!/bin/bash\n[ "$1" = apt-get ] || { echo "sudo refused: $*" >> "%s/state/sudo-refused"; exit 99; }\nexec "$@"\n' "$TEST_DIR" > bin/sudo
    # rm refuses anything under /tmp (outside this test's own directory, which lives
    # there on Linux) and records the attempt. These tests plant a
    # marker in the real /tmp, and a script that wipes /tmp must never be able to
    # do it to the machine running the tests (the glob is expanded before rm runs,
    # so the entries arrive as /tmp/<name>).
    cat > bin/rm <<STUB
#!/bin/bash
for a in "\$@"; do
    case "\$a" in
        "$TEST_DIR" | "$TEST_DIR"/*) ;;
        /tmp | /tmp/* | /private/tmp | /private/tmp/*)
            echo "\$a" >> "$TEST_DIR/state/rm-tmp-attempts"
            exit 0
            ;;
    esac
done
exec "$REAL_RM" "\$@"
STUB
    cat > bin/apt-get <<STUB
#!/bin/bash
echo "apt-get \$*" >> "$TEST_DIR/state/apt-calls"
exit 0
STUB
    chmod +x bin/docker bin/sudo bin/apt-get bin/rm

    export PATH="$TEST_DIR/bin:$PATH"
    export HOME="$TEST_DIR/home"

    # A file in the real /tmp that belongs to "another program"
    TMP_MARKER="/tmp/cleanup-system-test-marker-$$"
    echo live > "$TMP_MARKER"
}

teardown() {
    # The real rm, not the refusing stub from setup
    "$REAL_RM" -f "$TMP_MARKER"
    cd / || true
    "$REAL_RM" -rf "$TEST_DIR"
}

# tests/helpers/bats-assert is a minimal stub (exact assert_output, regex
# assert_line, no refute), so substring checks are done here, as fixed strings.
has() { [[ "$output" == *"$1"* ]] || { echo "expected output to contain: $1"; echo "got: $output"; return 1; }; }
lacks() { [[ "$output" != *"$1"* ]] || { echo "expected output NOT to contain: $1"; echo "got: $output"; return 1; }; }

clean() { "$TEST_DIR/scripts/cleanup-system.sh" < /dev/null; }

# Fails the test when any recorded docker call matches. (A bare `! grep` does not
# fail a Bats test, which is what shellcheck's SC2314 is about.)
docker_never_called() {
    # No file means docker was never called, so nothing unexpected was. (Whether it
    # should have been called is for the positive checks beside this one.)
    [ -f state/docker-calls ] || return 0
    if grep -qE "$@" state/docker-calls; then
        echo "unexpected docker call:"
        grep -E "$@" state/docker-calls
        return 1
    fi
}

# old <path>: a file last modified in 2020
old() { mkdir -p "$(dirname "$1")"; echo data > "$1"; touch -t 202001010000 "$1"; }
# fresh <path>: a file modified just now
fresh() { mkdir -p "$(dirname "$1")"; echo data > "$1"; }

# -- backups ---------------------------------------------------------------------

@test "backups are never deleted, however old and however many" {
    # The script used to delete every .tar.gz older than 30 days once there were
    # more than 10, which could leave a single backup and took the safety backups
    # made when a world is deleted
    local i
    for i in 01 02 03 04 05 06 07 08 09 10 11 12; do
        old "backups/minecraft_backup_202001${i}_000000.tar.gz"
    done
    old "backups/doomed.deleted.20200101_000000.tar.gz"
    old "backups/world_survival_20200101_000000.tar.gz"
    old "backups/minecraft_secrets_20200101_000000.tar.age"

    # Every file, hidden ones included, before and after
    local before after
    before="$(find backups -type f | sort)"
    [ -n "$before" ]

    run clean
    assert_success

    after="$(find backups -type f | sort)"
    [ "$before" = "$after" ]
    [ -f backups/doomed.deleted.20200101_000000.tar.gz ]
    has "Left alone"
}

@test "with few backups it still leaves them alone" {
    old "backups/minecraft_backup_20200101_000000.tar.gz"

    run clean
    assert_success
    [ -f backups/minecraft_backup_20200101_000000.tar.gz ]
}

# -- /tmp and ~/.cache -----------------------------------------------------------

@test "other programs' files in /tmp are left alone" {
    run clean
    assert_success
    [ "$(cat "$TMP_MARKER")" = "live" ]
    # and it never even tried (rm is stubbed to refuse /tmp, see setup)
    [ ! -e state/rm-tmp-attempts ]
}

@test "nothing is run through sudo except apt-get" {
    run clean
    assert_success
    [ ! -e state/sudo-refused ]
}

@test "only the pip cache is removed from ~/.cache" {
    mkdir -p "$HOME/.cache/pip" "$HOME/.cache/other-tool"
    echo x > "$HOME/.cache/pip/wheel"
    echo keep > "$HOME/.cache/other-tool/state"

    run clean
    assert_success
    [ ! -e "$HOME/.cache/pip" ]
    [ "$(cat "$HOME/.cache/other-tool/state")" = "keep" ]
}

# -- Docker --------------------------------------------------------------------------

@test "docker is pruned conservatively: dangling images and old build cache only" {
    run clean
    assert_success

    grep -q "docker image prune -f" state/docker-calls
    grep -q "docker builder prune -f --filter until=168h" state/docker-calls
    docker_never_called -- '--volumes'
    docker_never_called 'system prune'
    docker_never_called 'prune .*(-a|--all)'
}

@test "a failing docker prune is reported and does not stop the clean-up" {
    touch state/prune-fails

    run clean
    assert_success
    has "Could not prune Docker images"
    has "Could not prune the Docker build cache"
    has "Docker cleaned with warnings"
    lacks "✓ Docker cleaned"
    has "Cleanup complete"
}

@test "a clean docker prune says plainly that it worked" {
    run clean
    assert_success
    has "✓ Docker cleaned"
    lacks "with warnings"
}

# -- logs -----------------------------------------------------------------------------

@test "old compressed game logs and old application logs are removed, recent ones kept" {
    old "data/logs/2020-01-01-1.log.gz"
    fresh "data/logs/2999-01-01-1.log.gz"
    old "data/logs/latest.log"
    old "logs/deploy.log"
    fresh "logs/api.log"

    run clean
    assert_success

    [ ! -e data/logs/2020-01-01-1.log.gz ]
    [ -e data/logs/2999-01-01-1.log.gz ]
    # latest.log is the live log, not a rotated archive: never touched
    [ -e data/logs/latest.log ]
    [ ! -e logs/deploy.log ]
    [ -e logs/api.log ]
}

# -- caches ---------------------------------------------------------------------------

@test "python and node build caches are removed, source files are not" {
    mkdir -p api/blueprints/__pycache__ web/node_modules/.cache web/src
    echo x > api/blueprints/__pycache__/a.cpython-312.pyc
    echo x > web/node_modules/.cache/blob
    echo keep > api/server.py
    echo keep > web/src/App.jsx

    run clean
    assert_success

    [ ! -e api/blueprints/__pycache__ ]
    [ ! -e web/node_modules/.cache ]
    [ "$(cat api/server.py)" = "keep" ]
    [ "$(cat web/src/App.jsx)" = "keep" ]
}

@test "the apt cache is cleaned through sudo" {
    run clean
    assert_success
    grep -q "apt-get clean" state/apt-calls
}

# -- report ---------------------------------------------------------------------------

@test "it ends with a disk usage report" {
    run clean
    assert_success
    has "Disk Usage Report"
    has "Cleanup complete"
}
