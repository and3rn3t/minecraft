#!/usr/bin/env bats
# Unit Tests: backup-secrets.sh
#
# age is stubbed on PATH as a pass-through (reads stdin, writes it verbatim to
# the file named by -o) -- these tests exercise the shell orchestration
# (which paths get archived, upload gating, error handling), not real
# encryption. HOME is sandboxed to a scratch directory: SECRET_PATHS includes
# ${HOME}/.cloudflared and ${HOME}/playit/secret.toml, and a test must never
# create those under the real developer's home directory.

load '../helpers/bats-support/load'
load '../helpers/bats-assert/load'

setup() {
    REPO_DIR="$(cd "$BATS_TEST_DIRNAME/../.." && pwd)"
    TEST_DIR="$(mktemp -d)"
    cp -R "$REPO_DIR/scripts" "$TEST_DIR/scripts"
    mkdir -p "$TEST_DIR/config" "$TEST_DIR/backups" "$TEST_DIR/bin" "$TEST_DIR/home"
    cd "$TEST_DIR" || exit 1

    STATE_DIR="$TEST_DIR/state"
    mkdir -p "$STATE_DIR"
    : > "$STATE_DIR/calls"

    cat > bin/age <<STUB
#!/bin/bash
echo "age \$*" >> "$STATE_DIR/calls"
[ -f "$STATE_DIR/age-fails" ] && exit 1
out="" prev=""
for arg in "\$@"; do
    [ "\$prev" = "-o" ] && out="\$arg"
    prev="\$arg"
done
cat > "\$out"
exit 0
STUB
    chmod +x bin/age

    cat > bin/curl <<STUB
#!/bin/bash
echo "curl \$*" >> "$STATE_DIR/calls"
exit 0
STUB
    chmod +x bin/curl

    for provider in r2 s3 b2; do
        cat > "scripts/cloud-backup-${provider}.sh" <<STUB
#!/bin/bash
echo "cloud-backup-${provider}.sh \$*" >> "$STATE_DIR/calls"
[ -f "$STATE_DIR/${provider}-upload-fails" ] && exit 1
exit 0
STUB
        chmod +x "scripts/cloud-backup-${provider}.sh"
    done

    export PATH="$TEST_DIR/bin:$PATH"
    export HOME="$TEST_DIR/home"
    echo 'AGE_RECIPIENT="age1testrecipient"' > config/backup-secrets.conf
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

@test "fails and notifies when age is not installed" {
    rm -f bin/age
    # A real age elsewhere on PATH (e.g. Homebrew) would still be found, so
    # drop every PATH directory that provides one.
    local dir kept=""
    local IFS=:
    for dir in $PATH; do
        [ -x "$dir/age" ] || kept="${kept:+$kept:}$dir"
    done
    PATH="$kept"
    echo "NTFY_URL=http://example.invalid/topic" > config/notify.conf

    run scripts/backup-secrets.sh
    assert_failure
    assert_line "age is not installed"
    assert_called "example.invalid"
}

@test "fails when AGE_RECIPIENT is not configured" {
    : > config/backup-secrets.conf

    run scripts/backup-secrets.sh
    assert_failure
    assert_line "AGE_RECIPIENT is not set"
}

@test "warns and exits successfully when none of the secret paths exist" {
    run scripts/backup-secrets.sh
    assert_success
    assert_line "nothing to back up"
    run bash -c 'ls backups/minecraft_secrets_*.tar.age 2>/dev/null'
    assert_output ""
}

@test "archives the secret paths that exist and skips the ones that don't" {
    mkdir -p config
    echo '{}' > config/users.json
    echo '{}' > config/api-keys.json
    mkdir -p "$HOME/.cloudflared"
    echo "cert" > "$HOME/.cloudflared/cert.pem"
    # config/api.conf, config/oauth.conf, config/rcon.conf and
    # $HOME/playit/secret.toml are deliberately left absent.

    run scripts/backup-secrets.sh
    assert_success
    assert_line "Skipping secrets backup path (not present)"

    local archive
    archive="$(ls backups/minecraft_secrets_*.tar.age 2>/dev/null | head -1)"
    [ -n "$archive" ]
    run tar -tf "$archive"
    assert_success
    assert_line "users.json"
}

@test "fails and notifies when the archive step itself fails" {
    mkdir -p config
    echo '{}' > config/users.json
    touch "$STATE_DIR/age-fails"
    echo "NTFY_URL=http://example.invalid/topic" > config/notify.conf

    run scripts/backup-secrets.sh
    assert_failure
    assert_line "Secrets backup failed"
    assert_called "example.invalid"
}

@test "does not upload when no provider has AUTO_UPLOAD set" {
    mkdir -p config
    echo '{}' > config/users.json

    run scripts/backup-secrets.sh
    assert_success
    assert_not_called "cloud-backup-r2.sh upload"
}

@test "uploads to a provider with AUTO_UPLOAD set" {
    mkdir -p config
    echo '{}' > config/users.json
    echo 'AUTO_UPLOAD="true"' > config/cloud-backup-r2.conf

    run scripts/backup-secrets.sh
    assert_success
    assert_called "cloud-backup-r2.sh upload"
}

@test "notifies when the offsite upload fails, but the local archive still counts as success" {
    mkdir -p config
    echo '{}' > config/users.json
    echo 'AUTO_UPLOAD="true"' > config/cloud-backup-r2.conf
    touch "$STATE_DIR/r2-upload-fails"
    echo "NTFY_URL=http://example.invalid/topic" > config/notify.conf

    run scripts/backup-secrets.sh
    assert_success
    assert_called "example.invalid"
}
