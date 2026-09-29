#!/bin/bash
# Push notifications via ntfy (https://ntfy.sh or a self-hosted server).
#
# Source it from a script in scripts/, after lib/common.sh:
#     # shellcheck source=lib/notify.sh
#     source "$(dirname "${BASH_SOURCE[0]}")/lib/notify.sh"
#
# Reads config/notify.conf for NTFY_URL. Never fails the caller: a broken or
# unreachable ntfy endpoint must not turn a working backup, deploy or health
# check into a failed one.

# Guard against being sourced twice
if [ -n "${MINECRAFT_NOTIFY_SH_LOADED:-}" ]; then
    return 0
fi
MINECRAFT_NOTIFY_SH_LOADED=1

NOTIFY_CONFIG="${NOTIFY_CONFIG:-${PROJECT_DIR}/config/notify.conf}"
if [ -f "$NOTIFY_CONFIG" ]; then
    # shellcheck source=/dev/null
    source "$NOTIFY_CONFIG"
fi

# notify <title> <message> [priority]
# No-ops silently when NTFY_URL is unset, so this is safe to call
# unconditionally from every failure path.
notify() {
    local title="$1" message="$2" priority="${3:-default}"
    [ -n "${NTFY_URL:-}" ] || return 0
    curl -fsS -m 10 \
        -H "Title: ${title}" \
        -H "Priority: ${priority}" \
        -d "${message}" \
        "$NTFY_URL" >/dev/null 2>&1 || true
}

# notify_once <marker-file> <title> <message> [priority]
# Like notify, but only once per ongoing failure: no-ops if <marker-file>
# already exists, then creates it. Callers must remove the marker themselves
# once the condition clears, so the next failure notifies again. Without this,
# a condition that persists across many runs of a frequently-scheduled script
# (a stuck deploy, a still-unhealthy container) would notify on every run.
#
# Does nothing at all, including creating the marker, when NTFY_URL is unset:
# otherwise enabling ntfy mid-episode could never notify for that episode,
# since the marker would already exist from runs before it was configured.
notify_once() {
    local marker="$1" title="$2" message="$3" priority="${4:-default}"
    [ -n "${NTFY_URL:-}" ] || return 0
    [ -f "$marker" ] && return 0
    notify "$title" "$message" "$priority"
    mkdir -p "$(dirname "$marker")"
    touch "$marker"
}
