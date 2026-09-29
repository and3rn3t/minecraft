#!/usr/bin/env bats
# Unit Tests: backup-scheduler.sh
#
# manage.sh, cleanup-backups.sh, cloud-backup-r2.sh and backup-secrets.sh are
# replaced with stubs in the copied scripts/ tree (backup-scheduler.sh calls
# them by path, not via PATH), each logging its invocation to $STATE_DIR/calls.
# curl is stubbed on PATH for scripts/lib/notify.sh.

load '../helpers/bats-support/load'
load '../helpers/bats-assert/load'

setup() {
    REPO_DIR="$(cd "$BATS_TEST_DIRNAME/../.." && pwd)"
    TEST_DIR="$(mktemp -d)"
    cp -R "$REPO_DIR/scripts" "$TEST_DIR/scripts"
    mkdir -p "$TEST_DIR/config" "$TEST_DIR/backups" "$TEST_DIR/bin"
    cd "$TEST_DIR" || exit 1

    STATE_DIR="$TEST_DIR/state"
    mkdir -p "$STATE_DIR"
    : > "$STATE_DIR/calls"

    cat > scripts/manage.sh <<STUB
#!/bin/bash
echo "manage.sh \$*" >> "$STATE_DIR/calls"
[ -f "$STATE_DIR/manage-fails" ] && exit 1
touch "$TEST_DIR/backups/minecraft_backup_\$(date +%Y%m%d_%H%M%S).tar.gz"
exit 0
STUB

    cat > scripts/cleanup-backups.sh <<STUB
#!/bin/bash
echo "cleanup-backups.sh \$*" >> "$STATE_DIR/calls"
exit 0
STUB

    cat > scripts/cloud-backup-r2.sh <<STUB
#!/bin/bash
echo "cloud-backup-r2.sh \$*" >> "$STATE_DIR/calls"
[ -f "$STATE_DIR/r2-upload-fails" ] && exit 1
exit 0
STUB

    cat > scripts/backup-secrets.sh <<STUB
#!/bin/bash
echo "backup-secrets.sh \$*" >> "$STATE_DIR/calls"
exit 0
STUB

    chmod +x scripts/manage.sh scripts/cleanup-backups.sh scripts/cloud-backup-r2.sh scripts/backup-secrets.sh

    cat > bin/curl <<STUB
#!/bin/bash
echo "curl \$*" >> "$STATE_DIR/calls"
exit 0
STUB
    chmod +x bin/curl
    export PATH="$TEST_DIR/bin:$PATH"

    # Under systemd (which this timer runs from) INVOCATION_ID is set, and
    # backup-scheduler.sh skips its own exact-minute time gate as a result.
    export INVOCATION_ID="test"
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

@test "runs the backup and cleanup on success" {
    run scripts/backup-scheduler.sh
    assert_success
    assert_called "manage.sh backup"
    assert_called "cleanup-backups.sh"
}

@test "skips a weekly backup on the wrong day" {
    echo 'BACKUP_FREQUENCY=weekly
BACKUP_WEEKLY_DAY=9999' > config/backup-schedule.conf

    run scripts/backup-scheduler.sh
    assert_success
    assert_line "Skipping backup (not scheduled"
    assert_not_called "manage.sh backup"
}

@test "runs a weekly backup on the configured day" {
    local today
    today="$(date +%w)"
    echo "BACKUP_FREQUENCY=weekly
BACKUP_WEEKLY_DAY=${today}" > config/backup-schedule.conf

    run scripts/backup-scheduler.sh
    assert_success
    assert_called "manage.sh backup"
}

@test "under cron (no INVOCATION_ID) skips outside the scheduled time" {
    unset INVOCATION_ID
    echo 'BACKUP_TIME=00:00' > config/backup-schedule.conf

    run scripts/backup-scheduler.sh
    assert_success
    assert_line "Skipping backup (current time"
    assert_not_called "manage.sh backup"
}

@test "under systemd (INVOCATION_ID set) ignores the time gate" {
    echo 'BACKUP_TIME=00:00' > config/backup-schedule.conf

    run scripts/backup-scheduler.sh
    assert_success
    assert_called "manage.sh backup"
}

@test "does not upload offsite when no cloud config is present" {
    run scripts/backup-scheduler.sh
    assert_success
    assert_not_called "cloud-backup-r2.sh upload"
}

@test "does not upload offsite when AUTO_UPLOAD is not true" {
    echo 'AUTO_UPLOAD="false"' > config/cloud-backup-r2.conf

    run scripts/backup-scheduler.sh
    assert_success
    assert_not_called "cloud-backup-r2.sh upload"
}

@test "uploads offsite when AUTO_UPLOAD is true" {
    echo 'AUTO_UPLOAD="true"' > config/cloud-backup-r2.conf

    run scripts/backup-scheduler.sh
    assert_success
    assert_called "cloud-backup-r2.sh upload"
}

@test "notifies when the offsite upload fails" {
    echo 'AUTO_UPLOAD="true"' > config/cloud-backup-r2.conf
    touch "$STATE_DIR/r2-upload-fails"
    echo "NTFY_URL=http://example.invalid/topic" > config/notify.conf

    run scripts/backup-scheduler.sh
    assert_success
    assert_called "curl"
}

@test "runs the secrets backup after a successful world backup" {
    run scripts/backup-scheduler.sh
    assert_success
    assert_called "backup-secrets.sh"
}

@test "notifies and exits non-zero when the backup itself fails" {
    touch "$STATE_DIR/manage-fails"
    echo "NTFY_URL=http://example.invalid/topic" > config/notify.conf

    run scripts/backup-scheduler.sh
    assert_failure
    assert_called "curl"
    assert_not_called "cleanup-backups.sh"
}
