#!/bin/bash
# Encrypted archive of everything the admin panel needs that isn't ./data:
# accounts, API keys, session/signing secrets, tunnel and playit credentials.
# An SD-card failure destroys these along with the world; manage.sh backup
# only tars ./data, so they have no backup of their own without this.
#
# Encrypted with age (https://age-encryption.org) against a public recipient
# key in config/backup-secrets.conf. Only the matching PRIVATE key, kept off
# the Pi entirely, can decrypt the result -- see config/backup-secrets.conf.example.
#
# Run by backup-scheduler.sh after a successful world backup. Kept as its own
# script so a missing `age` binary or recipient key logs an error here without
# turning the world backup itself into a failure.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source-path=SCRIPTDIR
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"
# shellcheck source=lib/notify.sh
source "${SCRIPT_DIR}/lib/notify.sh"

SECRETS_CONFIG="${SECRETS_CONFIG:-${PROJECT_DIR}/config/backup-secrets.conf}"
if [ -f "$SECRETS_CONFIG" ]; then
    # shellcheck source=/dev/null
    source "$SECRETS_CONFIG"
fi

BACKUP_DIR="${PROJECT_DIR}/backups"

# Paths gathered into the archive, relative to $PROJECT_DIR or $HOME. A
# missing path is skipped with a warning, not a failure: not every Pi has a
# playit agent or a cloudflared tunnel configured, and this script also runs
# on a developer's machine where none of these exist at all.
SECRET_PATHS=(
    "${PROJECT_DIR}/config/users.json"
    "${PROJECT_DIR}/config/api-keys.json"
    "${PROJECT_DIR}/config/api.conf"
    "${PROJECT_DIR}/config/oauth.conf"
    "${PROJECT_DIR}/config/rcon.conf"
    "${HOME}/.cloudflared"
    "${HOME}/playit/secret.toml"
)

# Function to create the encrypted archive. Prints the archive's path on
# success.
create_secrets_backup() {
    command -v age >/dev/null 2>&1 || {
        log_error "age is not installed; cannot encrypt the secrets backup (https://age-encryption.org)"
        return 1
    }
    [ -n "${AGE_RECIPIENT:-}" ] || {
        log_error "AGE_RECIPIENT is not set in ${SECRETS_CONFIG}; see config/backup-secrets.conf.example"
        return 1
    }

    local existing=() path
    for path in "${SECRET_PATHS[@]}"; do
        if [ -e "$path" ]; then
            existing+=("$path")
        else
            log_warn "Skipping secrets backup path (not present): $path"
        fi
    done
    if [ ${#existing[@]} -eq 0 ]; then
        log_warn "None of the configured secrets paths exist; nothing to back up"
        return 0
    fi

    mkdir -p "$BACKUP_DIR"
    local timestamp out
    timestamp="$(date +"%Y%m%d_%H%M%S")"
    out="${BACKUP_DIR}/minecraft_secrets_${timestamp}.tar.age"

    if tar -czf - "${existing[@]}" 2>/dev/null | age -r "$AGE_RECIPIENT" -o "$out"; then
        # log_success writes to stdout; this function's caller captures
        # stdout as the archive path, so the success message goes to stderr.
        log_success "Secrets backup created: $out" >&2
        echo "$out"
    else
        log_error "Secrets backup failed"
        rm -f "$out"
        return 1
    fi
}

# Function to upload the secrets archive offsite, same as backup-scheduler.sh
# does for the world backup: reads config/cloud-backup-<provider>.conf, only
# uploads when that provider's AUTO_UPLOAD="true". Best-effort -- the local
# archive this run just made is still good even if the upload fails.
upload_secrets_backup() {
    local file="$1" provider conf script status
    for provider in r2 s3 b2; do
        conf="${PROJECT_DIR}/config/cloud-backup-${provider}.conf"
        script="${SCRIPT_DIR}/cloud-backup-${provider}.sh"
        [ -f "$conf" ] || continue

        status=0
        (
            # shellcheck source=/dev/null
            source "$conf"
            [ "${AUTO_UPLOAD:-false}" = "true" ] || exit 3
            "$script" upload "$file"
        ) || status=$?

        case "$status" in
            0) log_success "Uploaded $(basename "$file") to ${provider}" ;;
            3) ;; # AUTO_UPLOAD not set for this provider; not an error
            *)
                log_error "Offsite upload of secrets backup to ${provider} failed"
                notify "Minecraft secrets backup" "Local secrets backup OK, but offsite upload to ${provider} failed" high
                ;;
        esac
    done
}

main() {
    local out
    if ! out="$(create_secrets_backup)"; then
        notify "Minecraft secrets backup failed" "See logs for details" high
        exit 1
    fi
    # An empty $out means nothing existed to back up, not a failure -- `if`
    # here (not `[ -n "$out" ] && ...`) so that legitimate case doesn't leave
    # this function's, and so the script's, exit status at the test's own 1.
    if [ -n "$out" ]; then
        upload_secrets_backup "$out"
    fi
}

main "$@"
