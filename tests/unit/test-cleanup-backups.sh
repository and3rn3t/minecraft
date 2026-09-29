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

# Prints a YYYYMMDD at least <min_days_ago> in the past that is neither a
# Sunday nor the 1st of the month, so it classifies as "daily" regardless of
# which real-world date the test happens to run on.
pick_daily_date() {
    local days_ago="$1" candidate dow dom
    while :; do
        candidate="$(date "-v-${days_ago}d" +%Y%m%d 2>/dev/null || date -d "${days_ago} days ago" +%Y%m%d)"
        dow="$(date -j -f %Y%m%d "$candidate" +%w 2>/dev/null || date -d "$candidate" +%w)"
        dom="$(date -j -f %Y%m%d "$candidate" +%d 2>/dev/null || date -d "$candidate" +%d)"
        [ "$dow" != "0" ] && [ "$dom" != "01" ] && { echo "$candidate"; return; }
        days_ago=$((days_ago + 1))
    done
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

    # 30 days ago, comfortably past the 7-day window -- but nudged forward a
    # day at a time if it happens to land on a Sunday or the 1st, which would
    # classify it as weekly/monthly and let it survive on their far more
    # generous default retention (30 and 365 days).
    local old_date
    old_date="$(pick_daily_date 30)"
    make_backup "$old_date" "${old_date}1200"

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
