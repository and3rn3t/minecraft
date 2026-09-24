#!/bin/bash
# Keep the Pi's checkout on the latest green commit of main, and apply only
# the parts of each change that need applying.
#
# Run every few minutes by systemd/minecraft-deploy.timer. The Pi pulls; nothing
# pushes into the house, so no inbound port and no CI runner on the machine
# that holds the world and its backups.
#
# One run:
#   1. Apply a game-server restart that an earlier run deferred, if the server
#      is now empty.
#   2. Fetch the branch. Stop if nothing is new, if the new commit has not
#      passed CI, or if this commit already failed to deploy once.
#   3. Fast-forward, then work out what changed across *every* commit since
#      the last deploy, not just the newest one.
#   4. Web panel -> fetch the build CI made, or build it here; swap it in
#      only after the API is known to be healthy.
#      systemd/  -> install the units and reload systemd.
#      api/      -> reinstall dependencies if they changed, restart the API,
#                   and wait for /api/health.
#      nginx     -> test the config and reload.
#      image     -> pull or rebuild, then restart the game server only when
#                   nobody is playing (a restart waits for an empty server).
#   5. If the web build, the dependencies or the API health check fail, go
#      back to the previous commit, restart what was restarted, and do not
#      retry this commit. A newer commit is tried as normal.
#
# Every deploy and rollback is written to the audit log, and optionally sent as
# a push notification (DEPLOY_NTFY_URL).

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source-path=SCRIPTDIR
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

DEPLOY_CONFIG="${DEPLOY_CONFIG:-${PROJECT_DIR}/config/deploy.conf}"
if [ -f "$DEPLOY_CONFIG" ]; then
    # shellcheck source=/dev/null
    source "$DEPLOY_CONFIG"
fi

DEPLOY_REMOTE="${DEPLOY_REMOTE:-origin}"
DEPLOY_BRANCH="${DEPLOY_BRANCH:-main}"
DEPLOY_WORKFLOW="${DEPLOY_WORKFLOW:-main.yml}"
DEPLOY_REQUIRE_CI="${DEPLOY_REQUIRE_CI:-true}"
DEPLOY_GITHUB_TOKEN="${DEPLOY_GITHUB_TOKEN:-}"
DEPLOY_NTFY_URL="${DEPLOY_NTFY_URL:-}"
DEPLOY_API_HEALTH_URL="${DEPLOY_API_HEALTH_URL:-http://127.0.0.1:8080/api/health}"
DEPLOY_HEALTH_TIMEOUT="${DEPLOY_HEALTH_TIMEOUT:-60}"
DEPLOY_API_SERVICE="${DEPLOY_API_SERVICE:-minecraft-api.service}"
GITHUB_API="${GITHUB_API:-https://api.github.com}"

STATE_DIR="${PROJECT_DIR}/.deploy"
FAILED_FILE="${STATE_DIR}/failed-commit"
PENDING_FILE="${STATE_DIR}/pending-server-restart"
DEPLOYED_FILE="${STATE_DIR}/last-deploy"
AUDIT_LOG_FILE="${AUDIT_LOG_FILE:-${PROJECT_DIR}/config/audit.log}"

SERVICE_NAME="minecraft"

# Paths whose change means the game server's image or container config changed.
# Not server.properties or eula.txt, although the Dockerfile copies them in:
# ./data is mounted over /minecraft/server, so the live copies are the ones in
# data/, which the admin panel edits. The tracked files only seed a new world.
IMAGE_PATHS_RE='^(Dockerfile|docker-compose[^/]*\.ya?ml|scripts/download-server\.sh|scripts/start\.sh)$'

usage() {
    echo "Usage: $0 {run|check|status|since <commit>}"
    echo ""
    echo "Commands:"
    echo "  run             - Deploy the newest green commit, if there is one"
    echo "  check           - Say what a run would do, change nothing"
    echo "  status          - Show the last deploy, any failed commit and any deferred restart"
    echo "  since <commit>  - Treat <commit> as the last one applied, so the next run"
    echo "                    applies everything after it (after a pull by hand:"
    echo "                    '$0 since ORIG_HEAD')"
    exit 1
}

# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------

short() { echo "${1:0:7}"; }

# Function to send a push notification, if configured. Never fails the deploy.
notify() {
    [ -n "$DEPLOY_NTFY_URL" ] || return 0
    curl -fsS -m 10 -H "Title: Minecraft server deploy" -d "$1" "$DEPLOY_NTFY_URL" >/dev/null 2>&1 || true
}

# Function to append an entry to the API's audit log (JSON lines)
audit() {
    local action="$1" details="$2"
    mkdir -p "$(dirname "$AUDIT_LOG_FILE")"
    python3 - "$action" "$details" >>"$AUDIT_LOG_FILE" 2>/dev/null <<'PY' || true
import json
import sys
from datetime import datetime, timezone

print(json.dumps({
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "username": "deploy-agent",
    "action": sys.argv[1],
    "details": json.loads(sys.argv[2]),
    "ip_address": "localhost",
}))
PY
}

# Function to print "owner/repo" from the remote URL
github_repo() {
    if [ -n "${DEPLOY_REPO:-}" ]; then
        echo "$DEPLOY_REPO"
        return
    fi
    git remote get-url "$DEPLOY_REMOTE" 2>/dev/null |
        sed -E -n 's#^.*github\.com[:/]([^/]+/[^/]+)$#\1#p' | sed -E 's#\.git$##'
}

# Function to print the auth header for curl's -H @file. Passing the token this
# way, rather than as an argument, keeps it out of `ps` for other local users.
auth_header() {
    printf 'Authorization: Bearer %s\n' "$DEPLOY_GITHUB_TOKEN"
}

# Function to GET a GitHub API path, authenticated when a token is configured
github_get() {
    if [ -n "$DEPLOY_GITHUB_TOKEN" ]; then
        curl -fsS -m 20 -H "Accept: application/vnd.github+json" -H @<(auth_header) "${GITHUB_API}$1"
    else
        curl -fsS -m 20 -H "Accept: application/vnd.github+json" "${GITHUB_API}$1"
    fi
}

# Function to report CI for a commit: success, pending, failure or unknown.
# Prints "<state> <run-id>".
ci_state() {
    local sha="$1" repo body
    repo="$(github_repo)"
    if [ -z "$repo" ]; then
        echo "unknown -"
        return
    fi
    if ! body="$(github_get "/repos/${repo}/actions/workflows/${DEPLOY_WORKFLOW}/runs?head_sha=${sha}&event=push&per_page=5")"; then
        echo "unknown -"
        return
    fi
    python3 -c '
import json, sys
runs = json.load(sys.stdin).get("workflow_runs") or []
if not runs:
    print("pending -")
else:
    run = runs[0]
    if run.get("status") != "completed":
        print("pending", run["id"])
    elif run.get("conclusion") == "success":
        print("success", run["id"])
    else:
        print("failure", run["id"])
' <<<"$body" 2>/dev/null || echo "unknown -"
}

# ---------------------------------------------------------------------------
# Game server restarts: only when nobody is online
# ---------------------------------------------------------------------------

server_is_running() {
    [ -n "$(compose ps --status running --quiet "$SERVICE_NAME" 2>/dev/null)" ]
}

# Function to recreate the game container if a change is waiting and it is safe
apply_pending_restart() {
    [ -f "$PENDING_FILE" ] || return 0

    if ! server_is_running; then
        # Stopped on purpose (bedtime, maintenance). It picks up the new image
        # and config whenever it is next started, so there is nothing to wait for.
        log_info "Game server is stopped; it will start on the new version"
        rm -f "$PENDING_FILE"
        return 0
    fi

    local online
    online="$(players_online 2>/dev/null)" || online=""
    case "$online" in
        '' | *[!0-9]*)
            log_warn "Game server update waiting: could not tell who is online"
            return 0
            ;;
    esac
    if [ "$online" -gt 0 ]; then
        log_info "Game server update waiting: ${online} player(s) online"
        return 0
    fi

    log_info "Server is empty; restarting the game server on the new version"
    if compose up -d "$SERVICE_NAME"; then
        rm -f "$PENDING_FILE"
        audit "deploy.server_restart" "{\"commit\": \"$(git rev-parse HEAD)\"}"
        notify "Game server restarted on $(short "$(git rev-parse HEAD)")"
    else
        log_error "Game server restart failed; will try again next run"
    fi
}

# ---------------------------------------------------------------------------
# Individual deploy steps
# ---------------------------------------------------------------------------

# Function to download the web build CI made for this run. Needs a token:
# artifact downloads are never anonymous, even on a public repository.
fetch_web_artifact() {
    local run_id="$1" dest="$2" repo url tmp
    [ -n "$DEPLOY_GITHUB_TOKEN" ] && [ "$run_id" != "-" ] || return 1
    repo="$(github_repo)"
    url="$(github_get "/repos/${repo}/actions/runs/${run_id}/artifacts?name=web-dist" |
        python3 -c 'import json,sys; a=json.load(sys.stdin).get("artifacts") or []; print(a[0]["archive_download_url"] if a and not a[0].get("expired") else "")' 2>/dev/null)" || return 1
    [ -n "$url" ] || return 1

    tmp="$(mktemp)"
    if ! curl -fsSL -m 120 -H @<(auth_header) -o "$tmp" "$url"; then
        rm -f "$tmp"
        return 1
    fi
    rm -rf "$dest"
    mkdir -p "$dest"
    python3 -m zipfile -e "$tmp" "$dest" >/dev/null 2>&1 || { rm -f "$tmp"; return 1; }
    rm -f "$tmp"
    [ -f "$dest/index.html" ]
}

# Function to check for build-time settings that exist only on the Pi. Vite
# bakes VITE_* values (the API URL) into the bundle, and these files are
# gitignored, so CI's build would not carry them.
web_has_local_env() {
    local f
    for f in .env .env.local .env.production .env.production.local; do
        [ -f "${PROJECT_DIR}/web/${f}" ] && return 0
    done
    return 1
}

# Function to build the web panel on the Pi
build_web_locally() {
    local dest="$1"
    command -v npm >/dev/null 2>&1 || { log_error "npm is not installed and CI's build could not be fetched"; return 1; }
    (
        cd "${PROJECT_DIR}/web" || exit 1
        npm ci --no-audit --no-fund && npx vite build --outDir "$dest" --emptyOutDir
    ) || return 1
    [ -f "$dest/index.html" ]
}

# Function to install unit files and reload systemd
install_units() {
    local unit
    for unit in "${PROJECT_DIR}"/systemd/*.service "${PROJECT_DIR}"/systemd/*.timer; do
        [ -f "$unit" ] || continue
        sudo -n cp "$unit" /etc/systemd/system/ || return 1
    done
    sudo -n systemctl daemon-reload
}

# Function to reinstall the API's Python dependencies
install_api_deps() {
    local venv="${PROJECT_DIR}/api/venv"
    [ -x "${venv}/bin/pip" ] || { log_error "No API virtualenv at ${venv}; run scripts/setup-api-venv.sh once"; return 1; }
    "${venv}/bin/pip" install --quiet -r "${PROJECT_DIR}/api/requirements.txt"
}

# Function to restart the API and wait until it answers its health check
restart_api() {
    sudo -n systemctl restart "$DEPLOY_API_SERVICE" || return 1
    local waited=0
    while [ "$waited" -lt "$DEPLOY_HEALTH_TIMEOUT" ]; do
        if curl -fsS -m 5 "$DEPLOY_API_HEALTH_URL" >/dev/null 2>&1; then
            return 0
        fi
        sleep 2
        waited=$((waited + 2))
    done
    return 1
}

# Function to swap a new web build into place, keeping the previous one
swap_web() {
    local new="$1" live="${PROJECT_DIR}/web/dist" prev="${STATE_DIR}/web-dist.prev"
    rm -rf "$prev"
    [ -d "$live" ] && mv "$live" "$prev"
    mv "$new" "$live"
}

# Function to prepare the game server's new image; the restart itself waits
# for an empty server
prepare_server_update() {
    if compose config 2>/dev/null | grep -qE '^[[:space:]]+build:'; then
        log_info "Rebuilding the game server image..."
        compose build "$SERVICE_NAME" || return 1
    else
        log_info "Pulling the game server image..."
        compose pull "$SERVICE_NAME" || return 1
    fi
    touch "$PENDING_FILE"
}

# ---------------------------------------------------------------------------
# The deploy
# ---------------------------------------------------------------------------

# Function to decide whether there is anything to deploy. Sets FROM, TO, RUN_ID.
# Returns 1 when there is nothing to do; the reason has been logged.
find_target() {
    local branch
    branch="$(git symbolic-ref --short HEAD 2>/dev/null)" || branch=""
    if [ "$branch" != "$DEPLOY_BRANCH" ]; then
        log_warn "Checkout is on '${branch:-a detached HEAD}', not '${DEPLOY_BRANCH}'; not deploying"
        return 1
    fi

    if ! git fetch --quiet "$DEPLOY_REMOTE" "$DEPLOY_BRANCH"; then
        log_warn "Could not fetch ${DEPLOY_REMOTE}/${DEPLOY_BRANCH}; trying again next run"
        return 1
    fi

    local head
    head="$(git rev-parse HEAD)"
    TO="$(git rev-parse "${DEPLOY_REMOTE}/${DEPLOY_BRANCH}")"
    RUN_ID="-"

    # Deploy from the last commit that was fully applied, not from HEAD. HEAD
    # can be ahead of it: a `git pull` by hand, or a run that died after the
    # fast-forward. Diffing from HEAD would call that "up to date" and never
    # restart what the pull changed.
    FROM="$(last_deployed)"
    if [ -z "$FROM" ]; then
        # First run: take the checkout as it stands as the starting point
        FROM="$head"
        [ "${DRY_RUN:-false}" = true ] || record_deployed "$FROM" "starting point"
    elif ! git merge-base --is-ancestor "$FROM" "$head" 2>/dev/null; then
        log_warn "The last deploy ($(short "$FROM")) is not in this checkout's history; starting from $(short "$head")"
        FROM="$head"
        [ "${DRY_RUN:-false}" = true ] || record_deployed "$FROM" "starting point"
    fi

    if [ "$FROM" = "$TO" ]; then
        log_info "Up to date at $(short "$FROM")"
        return 1
    fi

    if ! git merge-base --is-ancestor "$head" "$TO"; then
        log_warn "The checkout has commits that are not on ${DEPLOY_REMOTE}/${DEPLOY_BRANCH}; not deploying"
        return 1
    fi

    if ! git diff --quiet || ! git diff --cached --quiet; then
        log_warn "Tracked files have local edits; not deploying over them (see 'git status')"
        return 1
    fi

    if [ -f "$FAILED_FILE" ] && [ "$(cat "$FAILED_FILE")" = "$TO" ]; then
        log_info "$(short "$TO") failed to deploy before; waiting for a newer commit"
        return 1
    fi

    if [ "$DEPLOY_REQUIRE_CI" = "true" ]; then
        local state
        read -r state RUN_ID <<<"$(ci_state "$TO")"
        case "$state" in
            success) ;;
            pending)
                log_info "$(short "$TO") is still in CI; waiting"
                return 1
                ;;
            failure)
                log_warn "$(short "$TO") failed CI; not deploying it"
                return 1
                ;;
            *)
                log_warn "Could not read CI status for $(short "$TO"); trying again next run"
                return 1
                ;;
        esac
    fi
    return 0
}

# Function to print the last commit that was fully deployed, if one is recorded
last_deployed() {
    [ -f "$DEPLOYED_FILE" ] || return 0
    awk 'NR == 1 { print $1 }' "$DEPLOYED_FILE"
}

# Function to record a commit as fully deployed
record_deployed() {
    echo "$1 $(date -u +%Y-%m-%dT%H:%M:%SZ) $2" >"$DEPLOYED_FILE"
}

# Function to put everything back the way it was before this deploy
rollback() {
    local reason="$1"
    log_error "Deploy of $(short "$TO") failed: ${reason}. Rolling back to $(short "$FROM")"

    git reset --quiet --hard "$FROM"
    if [ "$UNITS_CHANGED" = true ]; then
        install_units || log_error "Reinstalling the previous systemd units failed"
    fi
    rm -rf "${STATE_DIR}/web-dist.new"
    if [ "$WEB_SWAPPED" = true ] && [ -d "${STATE_DIR}/web-dist.prev" ]; then
        rm -rf "${PROJECT_DIR}/web/dist"
        mv "${STATE_DIR}/web-dist.prev" "${PROJECT_DIR}/web/dist"
    fi
    if [ "$DEPS_CHANGED" = true ]; then
        install_api_deps || log_error "Reinstalling the previous dependencies failed"
    fi
    if [ "$API_RESTARTED" = true ]; then
        restart_api || log_error "The API is not healthy after rolling back either; check ${DEPLOY_API_SERVICE}"
    fi

    echo "$TO" >"$FAILED_FILE"
    audit "deploy.rollback" "{\"from\": \"$FROM\", \"to\": \"$TO\", \"reason\": \"$reason\"}"
    notify "Deploy of $(short "$TO") failed (${reason}); rolled back to $(short "$FROM")"
    return 1
}

run_deploy() {
    cd "$PROJECT_DIR" || return 1
    mkdir -p "$STATE_DIR"

    # One run at a time, shared with auto-update.sh: a slow web build must not
    # overlap the next tick, and the hourly image check must not recreate the
    # container while this is rebuilding it
    if ! take_update_lock; then
        log_info "Another deploy or image update is running"
        return 0
    fi

    apply_pending_restart

    find_target || return 0

    local changed
    changed="$(git diff --name-only "$FROM" "$TO")"

    WEB_CHANGED=false
    API_CHANGED=false
    DEPS_CHANGED=false
    UNITS_CHANGED=false
    NGINX_CHANGED=false
    IMAGE_CHANGED=false
    WEB_SWAPPED=false
    API_RESTARTED=false
    grep -q '^web/' <<<"$changed" && WEB_CHANGED=true
    grep -q '^api/' <<<"$changed" && API_CHANGED=true
    grep -qx 'api/requirements.txt' <<<"$changed" && DEPS_CHANGED=true
    grep -q '^systemd/' <<<"$changed" && UNITS_CHANGED=true
    grep -qx 'config/nginx-minecraft.conf' <<<"$changed" && NGINX_CHANGED=true
    grep -qE "$IMAGE_PATHS_RE" <<<"$changed" && IMAGE_CHANGED=true

    log_info "Deploying $(short "$FROM") -> $(short "$TO")"
    if [ "$(git rev-parse HEAD)" != "$TO" ]; then
        git merge --quiet --ff-only "$TO"
    fi

    local new_web="${STATE_DIR}/web-dist.new"
    if [ "$WEB_CHANGED" = true ]; then
        if ! web_has_local_env && fetch_web_artifact "$RUN_ID" "$new_web"; then
            log_info "Using the web panel CI built"
        else
            log_info "Building the web panel here..."
            build_web_locally "$new_web" || { rollback "web build failed"; return 1; }
        fi
    fi

    if [ "$UNITS_CHANGED" = true ]; then
        # Not a rollback reason: the old units keep working
        install_units || log_warn "Could not install the systemd units (does this user have passwordless sudo?)"
    fi

    if [ "$DEPS_CHANGED" = true ]; then
        install_api_deps || { rollback "installing API dependencies failed"; return 1; }
    fi

    if [ "$API_CHANGED" = true ] || [ "$UNITS_CHANGED" = true ]; then
        API_RESTARTED=true
        restart_api || { rollback "the API did not pass its health check"; return 1; }
    fi

    if [ "$WEB_CHANGED" = true ]; then
        swap_web "$new_web"
        WEB_SWAPPED=true
    fi

    if [ "$NGINX_CHANGED" = true ]; then
        if sudo -n nginx -t >/dev/null 2>&1; then
            sudo -n systemctl reload nginx || log_warn "nginx reload failed"
        else
            log_warn "nginx rejected its config; not reloading. Run 'sudo nginx -t' to see why"
        fi
    fi

    if [ "$IMAGE_CHANGED" = true ]; then
        prepare_server_update || log_warn "Could not prepare the game server image; it stays on the current version"
        apply_pending_restart
    fi

    rm -f "$FAILED_FILE"
    local parts=()
    [ "$API_CHANGED" = true ] && parts+=(api)
    [ "$WEB_CHANGED" = true ] && parts+=(web)
    [ "$UNITS_CHANGED" = true ] && parts+=(systemd)
    [ "$NGINX_CHANGED" = true ] && parts+=(nginx)
    [ "$IMAGE_CHANGED" = true ] && parts+=(server)
    local summary="${parts[*]:-no service changes}"

    record_deployed "$TO" "$summary"
    audit "deploy.success" "{\"from\": \"$FROM\", \"to\": \"$TO\", \"applied\": \"$summary\"}"
    notify "Deployed $(short "$TO"): ${summary}"
    log_success "Deployed $(short "$TO") (${summary})"
}

check_deploy() {
    cd "$PROJECT_DIR" || return 1
    DRY_RUN=true
    mkdir -p "$STATE_DIR"
    if find_target; then
        log_info "Would deploy $(short "$FROM") -> $(short "$TO"), which touches:"
        git diff --name-only "$FROM" "$TO" | sed 's/^/  /'
    fi
    if [ -f "$PENDING_FILE" ]; then
        log_info "A game server restart is waiting for the server to be empty"
    fi
    return 0
}

# Function to set the starting point by hand, e.g. after a `git pull` that
# nothing has applied yet
set_since() {
    cd "$PROJECT_DIR" || return 1
    local sha
    if ! sha="$(git rev-parse --verify --quiet "${1:-}^{commit}")"; then
        log_error "Not a commit: ${1:-(none given)}"
        return 1
    fi
    if ! git merge-base --is-ancestor "$sha" HEAD; then
        log_error "$(short "$sha") is not in the history of the checkout"
        return 1
    fi
    mkdir -p "$STATE_DIR"
    record_deployed "$sha" "set by hand"
    log_success "The next run applies everything after $(short "$sha")"
}

show_status() {
    cd "$PROJECT_DIR" || return 1
    echo "Checkout:     $(git rev-parse --short HEAD 2>/dev/null) on $(git symbolic-ref --short HEAD 2>/dev/null || echo 'detached HEAD')"
    if [ -f "$DEPLOYED_FILE" ]; then
        echo "Last deploy:  $(cat "$DEPLOYED_FILE")"
    else
        echo "Last deploy:  none recorded"
    fi
    if [ -f "$FAILED_FILE" ]; then
        echo "Failed:       $(cat "$FAILED_FILE") (skipped until a newer commit lands)"
    fi
    if [ -f "$PENDING_FILE" ]; then
        echo "Waiting:      game server restart, until nobody is online"
    fi
}

main() {
    case "${1:-}" in
        run)
            run_deploy
            ;;
        check)
            check_deploy
            ;;
        status)
            show_status
            ;;
        since)
            set_since "${2:-}"
            ;;
        *)
            usage
            ;;
    esac
}

# Everything above is a function, so bash has read the whole file before any
# of it runs. The deploy replaces this file mid-run; this keeps it safe.
main "$@"
exit $?
