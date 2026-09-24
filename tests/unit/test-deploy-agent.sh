#!/usr/bin/env bats
# Unit Tests: deploy-agent.sh
#
# Each test gets a real git setup: a bare "GitHub" repository, a seed clone to
# push commits from, and the "Pi" clone the agent deploys. docker, sudo, curl,
# npm and npx are stubs whose behaviour is set through files in $STATE_DIR and
# whose calls are logged to $STATE_DIR/calls.
#
# tests/helpers/bats-assert is a minimal stub: assert_output matches exactly and
# assert_line greps, with no refute helpers. Negative checks are therefore
# written as an explicit grep whose failure is asserted.

load '../helpers/bats-support/load'
load '../helpers/bats-assert/load'

setup() {
    REPO_DIR="$(cd "$BATS_TEST_DIRNAME/../.." && pwd)"
    TEST_DIR="$(mktemp -d)"
    STATE_DIR="$TEST_DIR/state"
    mkdir -p "$STATE_DIR" "$TEST_DIR/bin"
    : > "$STATE_DIR/calls"

    # Hermetic git: the machine's own config (hooks, push settings) stays out
    export GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_NOSYSTEM=1
    export GIT_AUTHOR_NAME=test GIT_AUTHOR_EMAIL=test@example.com
    export GIT_COMMITTER_NAME=test GIT_COMMITTER_EMAIL=test@example.com

    git init -q --bare -b main "$TEST_DIR/remote.git"
    git clone -q "$TEST_DIR/remote.git" "$TEST_DIR/seed" 2>/dev/null
    (
        cd "$TEST_DIR/seed" || exit 1
        git checkout -q -b main
        cp -R "$REPO_DIR/scripts" scripts
        mkdir -p api web systemd config
        echo "print('api v1')" > api/server.py
        echo "flask" > api/requirements.txt
        echo '{"name": "web"}' > web/package.json
        echo "v1" > web/app.js
        echo "[Unit]" > systemd/minecraft-api.service
        echo "# docs" > README.md
        git add -A
        git commit -q -m "initial"
        git push -q origin main
    )
    git clone -q "$TEST_DIR/remote.git" "$TEST_DIR/pi"
    PI="$TEST_DIR/pi"

    # CI is green unless a test says otherwise; the API answers its health check
    echo '{"workflow_runs": [{"id": 42, "status": "completed", "conclusion": "success"}]}' > "$STATE_DIR/ci"
    echo 0 > "$STATE_DIR/health"
    echo 0 > "$STATE_DIR/players"
    echo "running" > "$STATE_DIR/ps"

    cat > "$TEST_DIR/bin/curl" <<STUB
#!/bin/bash
echo "curl \$*" >> "$STATE_DIR/calls"
url="\${*: -1}"
case "\$url" in
    *actions/workflows*) cat "$STATE_DIR/ci" ;;
    */api/health) exit "\$(cat "$STATE_DIR/health")" ;;
esac
exit 0
STUB

    cat > "$TEST_DIR/bin/sudo" <<STUB
#!/bin/bash
echo "sudo \$*" >> "$STATE_DIR/calls"
exit 0
STUB

    cat > "$TEST_DIR/bin/npm" <<STUB
#!/bin/bash
echo "npm \$*" >> "$STATE_DIR/calls"
exit 0
STUB

    # npx vite build --outDir <dir>: writes an index.html carrying web/app.js
    cat > "$TEST_DIR/bin/npx" <<STUB
#!/bin/bash
echo "npx \$*" >> "$STATE_DIR/calls"
[ -f "$STATE_DIR/build-fails" ] && exit 1
while [ \$# -gt 0 ]; do
    if [ "\$1" = "--outDir" ]; then out="\$2"; fi
    shift
done
mkdir -p "\$out"
cat app.js > "\$out/index.html"
STUB

    cat > "$TEST_DIR/bin/docker" <<STUB
#!/bin/bash
echo "docker \$*" >> "$STATE_DIR/calls"
case "\$*" in
    "compose version") echo "Docker Compose version v2.0.0" ;;
    *"ps --status running"*) cat "$STATE_DIR/ps" ;;
    *"compose config"*) printf 'services:\n  minecraft:\n    image: example\n' ;;
esac
exit 0
STUB

    chmod +x "$TEST_DIR"/bin/*
    export PATH="$TEST_DIR/bin:$PATH"
    export PLAYER_COUNT_CMD="cat $STATE_DIR/players"
    export DEPLOY_CONFIG="$TEST_DIR/no-such-deploy.conf"
    export DEPLOY_REPO="example/minecraft"
    export DEPLOY_HEALTH_TIMEOUT=2
    export AUDIT_LOG_FILE="$TEST_DIR/audit.log"
}

teardown() {
    cd /
    rm -rf "$TEST_DIR"
}

# Helper: commit a file change on "GitHub"
push_change() {
    local path="$1" content="$2"
    (
        cd "$TEST_DIR/seed" || exit 1
        mkdir -p "$(dirname "$path")"
        echo "$content" > "$path"
        git add -A
        git commit -q -m "change $path"
        git push -q origin main
    )
}

pi_head() { git -C "$PI" rev-parse HEAD; }
remote_head() { git -C "$TEST_DIR/seed" rev-parse HEAD; }

deploy() { run "$PI/scripts/deploy-agent.sh" "$@"; }

# Not written with `run`, which would overwrite the $output being asserted on
assert_called() {
    grep -q -- "$1" "$STATE_DIR/calls" || {
        echo "Expected a call matching: $1"
        return 1
    }
}

assert_not_called() {
    if grep -q -- "$1" "$STATE_DIR/calls"; then
        echo "Expected no call matching: $1"
        return 1
    fi
}

@test "deploy-agent.sh shows usage without a subcommand" {
    deploy
    assert_failure
    assert_line "Usage:"
}

@test "run does nothing when already up to date" {
    deploy run
    assert_success
    assert_line "Up to date"
    assert_not_called "sudo"
}

@test "run waits for a commit that is still in CI" {
    push_change api/server.py "print('api v2')"
    echo '{"workflow_runs": [{"id": 42, "status": "in_progress", "conclusion": null}]}' > "$STATE_DIR/ci"
    local before
    before="$(pi_head)"

    deploy run
    assert_success
    assert_line "still in CI"
    [ "$(pi_head)" = "$before" ]
}

@test "run treats a commit CI has not started on as pending" {
    push_change api/server.py "print('api v2')"
    echo '{"workflow_runs": []}' > "$STATE_DIR/ci"

    deploy run
    assert_success
    assert_line "still in CI"
}

@test "run never deploys a commit that failed CI" {
    push_change api/server.py "print('api v2')"
    echo '{"workflow_runs": [{"id": 42, "status": "completed", "conclusion": "failure"}]}' > "$STATE_DIR/ci"
    local before
    before="$(pi_head)"

    deploy run
    assert_success
    assert_line "failed CI"
    [ "$(pi_head)" = "$before" ]
    assert_not_called "sudo"
}

@test "run deploys an API change and restarts the API" {
    push_change api/server.py "print('api v2')"

    deploy run
    assert_success
    [ "$(pi_head)" = "$(remote_head)" ]
    assert_called "sudo -n systemctl restart minecraft-api.service"
    assert_line "Deployed"
    grep -q '"action": "deploy.success"' "$AUDIT_LOG_FILE"
}

@test "run restarts nothing for a docs-only change" {
    push_change README.md "# new docs"

    deploy run
    assert_success
    [ "$(pi_head)" = "$(remote_head)" ]
    assert_not_called "systemctl restart"
    assert_line "no service changes"
}

@test "run applies changes from every commit since the last deploy" {
    # The API change is in the older of the two commits. Comparing only the
    # newest commit with its parent would miss it.
    push_change api/server.py "print('api v2')"
    push_change README.md "# newer docs"

    deploy run
    assert_success
    assert_called "systemctl restart minecraft-api.service"
}

@test "run rolls back when the API fails its health check" {
    local before
    before="$(pi_head)"
    push_change api/server.py "print('broken')"
    echo 7 > "$STATE_DIR/health"

    deploy run
    assert_failure
    assert_line "Rolling back"
    [ "$(pi_head)" = "$before" ]
    [ "$(cat "$PI/.deploy/failed-commit")" = "$(remote_head)" ]
    grep -q '"action": "deploy.rollback"' "$AUDIT_LOG_FILE"
}

@test "run does not retry a commit that already failed" {
    push_change api/server.py "print('broken')"
    echo 7 > "$STATE_DIR/health"
    deploy run
    : > "$STATE_DIR/calls"

    deploy run
    assert_success
    assert_line "failed to deploy before"
    assert_not_called "systemctl restart"
}

@test "run tries a newer commit after a failed one" {
    push_change api/server.py "print('broken')"
    echo 7 > "$STATE_DIR/health"
    deploy run

    echo 0 > "$STATE_DIR/health"
    push_change api/server.py "print('fixed')"
    deploy run
    assert_success
    [ "$(pi_head)" = "$(remote_head)" ]
    [ ! -f "$PI/.deploy/failed-commit" ]
}

@test "run builds and swaps in the web panel" {
    push_change web/app.js "v2"

    deploy run
    assert_success
    [ "$(cat "$PI/web/dist/index.html")" = "v2" ]
}

@test "run keeps the old web panel when the build fails" {
    mkdir -p "$PI/web/dist"
    echo "v1" > "$PI/web/dist/index.html"
    local before
    before="$(pi_head)"
    push_change web/app.js "v2"
    touch "$STATE_DIR/build-fails"

    deploy run
    assert_failure
    assert_line "web build failed"
    [ "$(pi_head)" = "$before" ]
    [ "$(cat "$PI/web/dist/index.html")" = "v1" ]
}

@test "run builds on the Pi when web/.env holds local settings" {
    # Vite bakes VITE_API_URL into the bundle, so CI's build would be wrong here
    export DEPLOY_GITHUB_TOKEN="token"
    echo "VITE_API_URL=/api" > "$PI/web/.env"
    push_change web/app.js "v2"

    deploy run
    assert_success
    assert_not_called "artifacts"
    assert_called "npx vite build"
}

@test "run installs changed systemd units" {
    push_change systemd/minecraft-api.service "[Unit]
Description=changed"

    deploy run
    assert_success
    assert_called "sudo -n systemctl daemon-reload"
}

@test "run will not deploy over local edits to tracked files" {
    echo "edited on the Pi" >> "$PI/README.md"
    push_change api/server.py "print('api v2')"
    local before
    before="$(pi_head)"

    deploy run
    assert_success
    assert_line "local edits"
    [ "$(pi_head)" = "$before" ]
}

@test "run leaves a checkout on another branch alone" {
    git -C "$PI" checkout -q -b experiment
    push_change api/server.py "print('api v2')"

    deploy run
    assert_success
    assert_line "not 'main'"
}

@test "run waits for an empty server before restarting the game" {
    echo 2 > "$STATE_DIR/players"
    push_change Dockerfile "FROM example"

    deploy run
    assert_success
    assert_line "2 player(s) online"
    [ -f "$PI/.deploy/pending-server-restart" ]
    assert_not_called "up -d"

    echo 0 > "$STATE_DIR/players"
    deploy run
    assert_success
    assert_called "compose up -d minecraft"
    [ ! -f "$PI/.deploy/pending-server-restart" ]
}

@test "run does not start a stopped game server" {
    : > "$STATE_DIR/ps"
    push_change Dockerfile "FROM example"

    deploy run
    assert_success
    assert_not_called "up -d"
    [ ! -f "$PI/.deploy/pending-server-restart" ]
}

@test "run skips the CI check when told to" {
    export DEPLOY_REQUIRE_CI=false
    echo '{"workflow_runs": [{"id": 42, "status": "completed", "conclusion": "failure"}]}' > "$STATE_DIR/ci"
    push_change README.md "# docs, untested"

    deploy run
    assert_success
    [ "$(pi_head)" = "$(remote_head)" ]
}

@test "check reports what would deploy without deploying it" {
    local before
    before="$(pi_head)"
    push_change api/server.py "print('api v2')"

    deploy check
    assert_success
    assert_line "Would deploy"
    assert_line "api/server.py"
    [ "$(pi_head)" = "$before" ]
}

@test "run finishes applying a pull made by hand" {
    # HEAD moves without the agent: a `git pull` on the Pi, or a run that died
    # after the fast-forward. Diffing from HEAD would call this up to date.
    deploy run
    push_change api/server.py "print('api v2')"
    git -C "$PI" pull -q

    deploy run
    assert_success
    assert_line "Deployed"
    assert_called "systemctl restart minecraft-api.service"
}

@test "since ORIG_HEAD makes the first run apply the pull that installed the agent" {
    push_change api/server.py "print('api v2')"
    git -C "$PI" pull -q

    deploy since ORIG_HEAD
    assert_success

    deploy run
    assert_success
    assert_called "systemctl restart minecraft-api.service"
}

@test "since rejects something that is not a commit" {
    deploy since not-a-commit
    assert_failure
    assert_line "Not a commit"
}

@test "run does not touch the game server for server.properties" {
    # ./data is mounted over the image's copy, so there is nothing to apply
    push_change server.properties "motd=changed"

    deploy run
    assert_success
    assert_not_called "compose pull"
    assert_not_called "compose build"
    [ ! -f "$PI/.deploy/pending-server-restart" ]
}

@test "check records nothing, even on the first run" {
    deploy check
    assert_success
    [ ! -f "$PI/.deploy/last-deploy" ]
}

@test "a waiting game server restart is not applied from another branch" {
    # compose up reads the compose files as the checkout has them now
    echo 2 > "$STATE_DIR/players"
    push_change Dockerfile "FROM example"
    deploy run
    [ -f "$PI/.deploy/pending-server-restart" ]

    git -C "$PI" checkout -q -b experiment
    echo 0 > "$STATE_DIR/players"
    : > "$STATE_DIR/calls"
    deploy run
    assert_line "not a clean main"
    assert_not_called "up -d"
    [ -f "$PI/.deploy/pending-server-restart" ]
}

@test "a waiting game server restart is not applied over edited compose files" {
    echo 2 > "$STATE_DIR/players"
    push_change docker-compose.yml "services: {}"
    deploy run
    [ -f "$PI/.deploy/pending-server-restart" ]

    echo "services: {edited: {}}" > "$PI/docker-compose.yml"
    echo 0 > "$STATE_DIR/players"
    : > "$STATE_DIR/calls"
    deploy run
    assert_line "not a clean main"
    assert_not_called "up -d"
}
