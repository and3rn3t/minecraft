#!/usr/bin/env bats
# Unit Tests: cleanup-backups.sh
#
# Backup files are named minecraft_backup_YYYYMMDD_HHMMSS.tar.gz; the script
# classifies each by that embedded date (not mtime) as daily/weekly/monthly,
# and keeps the newest KEEP_LAST_N regardless of classification. Tests set
# each fake backup's mtime with `touch -t` to control ordering, since
# KEEP_LAST_N is evaluated by modification time, newest first.

load '../helpers/bats-support/load'
load '../helpers/bats-assert/load'

setup() {
    REPO_DIR="$(cd "$BATS_TEST_DIRNAME/../.." && pwd)"
    TEST_DIR="$(mktemp -d)"
    cp -R "$REPO_DIR/scripts" "$TEST_DIR/scripts"
    mkdir -p "$TEST_DIR/config" "$TEST_DIR/backups"
    cd "$TEST_DIR" || exit 1
}

teardown() {
    cd /
    rm -rf "$TEST_DIR"
}

# make_backup <date YYYYMMDD> <mtime YYYYMMDDHHMM>
make_backup() {
    local mtime="$2" file="backups/minecraft_backup_${1}_120000.tar.gz"
    echo "x" > "$file"
    touch -t "$mtime" "$file"
}

@test "reports nothing to clean up when the backup directory is empty" {
    run scripts/cleanup-backups.sh
    assert_success
    assert_line "No backups found"
}

@test "keeps the last N backups regardless of age" {
    echo 'KEEP_LAST_N=2
KEEP_DAILY_DAYS=0
KEEP_WEEKLY_DAYS=0
KEEP_MONTHLY_DAYS=0' > config/backup-retention.conf

    # Three backups, all otherwise outside every retention window (0 days),
    # dated on weekdays (not the 1st, not a Sunday) so they classify as daily.
    make_backup 20240102 202401021200 # Tuesday, oldest
    make_backup 20240104 202401041200 # Thursday, newest
    make_backup 20240103 202401031200 # Wednesday, middle

    run scripts/cleanup-backups.sh
    assert_success
    assert_line "kept 2, deleted 1 backup(s)"
    [ ! -f backups/minecraft_backup_20240102_120000.tar.gz ]
    [ -f backups/minecraft_backup_20240103_120000.tar.gz ]
    [ -f backups/minecraft_backup_20240104_120000.tar.gz ]
}

@test "deletes a daily backup older than KEEP_DAILY_DAYS" {
    echo 'KEEP_LAST_N=0
KEEP_DAILY_DAYS=7' > config/backup-retention.conf
    local old_date
    old_date="$(date -v-30d +%Y%m%d 2>/dev/null || date -d '30 days ago' +%Y%m%d)"
    make_backup "$old_date" "$(date -v-30d +%Y%m%d%H%M 2>/dev/null || date -d '30 days ago' +%Y%m%d%H%M)"

    run scripts/cleanup-backups.sh
    assert_success
    [ ! -f "backups/minecraft_backup_${old_date}_120000.tar.gz" ]
}

@test "keeps a monthly backup within KEEP_MONTHLY_DAYS" {
    echo 'KEEP_LAST_N=0
KEEP_DAILY_DAYS=0
KEEP_WEEKLY_DAYS=0
KEEP_MONTHLY_DAYS=365' > config/backup-retention.conf

    # The 1st of the current month: classifies as monthly regardless of
    # weekday, and is guaranteed to be within KEEP_MONTHLY_DAYS=365.
    local first_of_month
    first_of_month="$(date +%Y%m01)"
    make_backup "$first_of_month" "${first_of_month}1200"

    run scripts/cleanup-backups.sh
    assert_success
    [ -f "backups/minecraft_backup_${first_of_month}_120000.tar.gz" ]
}
