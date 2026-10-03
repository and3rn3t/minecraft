#!/usr/bin/env bats
# Unit Tests: plugin-manager.sh
#
# The script reads plugin.yml out of jars with unzip and moves jars between
# plugins/, plugins/disabled/ and backups/plugins/. Everything runs in a
# throwaway copy of the repo with a stubbed docker; jars are built with python's
# zipfile so no zip binary is needed. The script prompts with `read -n 1`, so
# confirmations are answered through stdin (see yes_to / no_to).

load '../helpers/bats-support/load'
load '../helpers/bats-assert/load'

setup() {
    REPO_DIR="$(cd "$BATS_TEST_DIRNAME/../.." && pwd)"
    TEST_DIR="$(mktemp -d)"
    cp -R "$REPO_DIR/scripts" "$TEST_DIR/scripts"
    mkdir -p "$TEST_DIR/bin" "$TEST_DIR/state" "$TEST_DIR/src"
    cd "$TEST_DIR" || exit 1

    # docker: the server counts as running while state/running exists; every
    # `docker exec` is logged, and fails while state/exec-fails exists
    cat > bin/docker <<STUB
#!/bin/bash
echo "docker \$*" >> "$TEST_DIR/state/docker-calls"
case "\$1" in
    ps)
        [ -f "$TEST_DIR/state/running" ] && echo "minecraft-server"
        exit 0
        ;;
    exec)
        [ -f "$TEST_DIR/state/exec-fails" ] && exit 1
        exit 0
        ;;
esac
exit 0
STUB
    chmod +x bin/docker
    export PATH="$TEST_DIR/bin:$PATH"

    # Plugins need a server that supports them; individual tests change this
    export SERVER_TYPE=paper
    unset MINECRAFT_VERSION
}

teardown() {
    cd / || true
    rm -rf "$TEST_DIR"
}

# tests/helpers/bats-assert is a minimal stub (exact assert_output, regex
# assert_line, no refute), so substring checks are done here, as fixed strings.
has() { [[ "$output" == *"$1"* ]] || { echo "expected output to contain: $1"; echo "got: $output"; return 1; }; }
lacks() { [[ "$output" != *"$1"* ]] || { echo "expected output NOT to contain: $1"; echo "got: $output"; return 1; }; }

# stdin is /dev/null unless an answer is piped in, so a prompt nobody expected
# cancels instead of hanging the suite
pm() { "$TEST_DIR/scripts/plugin-manager.sh" "$@" < /dev/null; }
yes_to() { printf 'y' | "$TEST_DIR/scripts/plugin-manager.sh" "$@"; }
no_to() { printf 'n' | "$TEST_DIR/scripts/plugin-manager.sh" "$@"; }

# make_jar <path> <plugin.yml text> [member name]
make_jar() {
    python3 - "$1" "$2" "${3:-plugin.yml}" <<'PY'
import sys, zipfile
path, content, member = sys.argv[1:4]
with zipfile.ZipFile(path, "w") as z:
    z.writestr(member, content)
PY
}

# yml <name> <version> [extra lines...]
yml() {
    local name="$1" version="$2"
    shift 2
    printf 'name: %s\nversion: %s\nmain: example.Main\n' "$name" "$version"
    local line
    for line in "$@"; do printf '%s\n' "$line"; done
}

# jar <name> <version> [extra yml lines...]: a source jar src/<name>.jar
jar() {
    local name="$1" version="$2"
    shift 2
    make_jar "$TEST_DIR/src/$name.jar" "$(yml "$name" "$version" "$@")"
}

# installed <name> <version> [extra yml lines...]: a jar already in plugins/
installed() {
    local name="$1" version="$2"
    shift 2
    mkdir -p "$TEST_DIR/plugins"
    make_jar "$TEST_DIR/plugins/$name.jar" "$(yml "$name" "$version" "$@")"
}

# -- usage ------------------------------------------------------------------

@test "no command prints usage and exits non-zero" {
    run pm
    assert_failure
    has "Usage:"
    has "list-json"
}

@test "an unknown command prints usage and exits non-zero" {
    run pm frobnicate
    assert_failure
    has "Usage:"
}

@test "commands that need an argument say so" {
    local cmd
    for cmd in install enable disable remove; do
        run pm "$cmd"
        assert_failure
        has "not specified"
    done
    run pm update onlyname
    assert_failure
    has "Plugin name and new file required"
}

# -- list / list-json ----------------------------------------------------------

@test "list-json is an empty array when nothing is installed" {
    run pm list-json
    assert_success
    assert_output "[]"
}

@test "list says so when nothing is installed" {
    run pm list
    assert_success
    has "No plugins installed"
}

@test "list-json reports name, version, filename and whether it is enabled" {
    installed Alpha 1.2.3
    mkdir -p plugins/disabled
    make_jar plugins/disabled/Beta.jar "$(yml Beta 4.5.6)"

    run pm list-json
    assert_success

    run python3 - "$output" <<'PY'
import json, sys
plugins = {p["name"]: p for p in json.loads(sys.argv[1])}
assert plugins["Alpha"] == {"name": "Alpha", "version": "1.2.3", "filename": "Alpha.jar", "enabled": True}, plugins
assert plugins["Beta"] == {"name": "Beta", "version": "4.5.6", "filename": "Beta.jar", "enabled": False}, plugins
PY
    assert_success
}

@test "a jar with no plugin.yml is listed under its filename" {
    mkdir -p plugins
    make_jar plugins/mystery.jar "nothing useful" "readme.txt"

    run pm list-json
    assert_success
    has '"name":"mystery.jar"'
    has '"enabled":true'
}

@test "paper-plugin.yml is read too" {
    mkdir -p plugins
    make_jar plugins/Papery.jar "$(yml Papery 9.9.9)" "paper-plugin.yml"

    run pm list-json
    assert_success
    has '"name":"Papery"'
    has '"version":"9.9.9"'
}

@test "list-json stays valid JSON for a plugin name containing quotes" {
    mkdir -p plugins
    make_jar plugins/odd.jar 'name: Odd"Name
version: 1.0
'

    run pm list-json
    assert_success
    run python3 -c 'import json,sys; d=json.loads(sys.argv[1]); assert d[0]["name"]=="Odd\"Name", d' "$output"
    assert_success
}

@test "list shows each plugin, a total and the disabled count" {
    installed Alpha 1.2.3
    installed Gamma 7.0
    mkdir -p plugins/disabled
    make_jar plugins/disabled/Beta.jar "$(yml Beta 4.5.6)"

    run pm list
    assert_success
    has "Alpha (v1.2.3) - Alpha.jar"
    has "Total: 2 plugin(s)"
    has "Disabled Plugins: 1"
}

# -- install -----------------------------------------------------------------------

@test "install of a file that does not exist fails" {
    run pm install nosuch.jar
    assert_failure
    has "Plugin file not found"
}

@test "install refuses anything that is not a .jar" {
    echo data > src/readme.txt

    run pm install src/readme.txt
    assert_failure
    has "must be a .jar file"
}

@test "install copies the jar into plugins/" {
    jar Alpha 1.2.3

    run pm install src/Alpha.jar
    assert_success
    has "Installing plugin: Alpha (v1.2.3)"
    has "Plugin installed: Alpha.jar"
    [ -f plugins/Alpha.jar ]
}

@test "install on a vanilla server warns, and answering no cancels" {
    jar Alpha 1.2.3

    SERVER_TYPE=vanilla run no_to install src/Alpha.jar
    assert_failure
    has "Vanilla server does not support plugins"
    has "Installation cancelled"
    [ ! -f plugins/Alpha.jar ]
}

@test "install on a vanilla server, answering yes, goes ahead" {
    jar Alpha 1.2.3

    SERVER_TYPE=vanilla run yes_to install src/Alpha.jar
    assert_success
    [ -f plugins/Alpha.jar ]
}

@test "install over an existing plugin, answering no, leaves it alone" {
    installed Alpha 1.0.0
    jar Alpha 2.0.0

    run no_to install src/Alpha.jar
    assert_failure
    has "Plugin already exists"
    run pm list-json
    has '"version":"1.0.0"'
}

@test "install over an existing plugin, answering yes, backs the old one up" {
    installed Alpha 1.0.0
    jar Alpha 2.0.0

    run yes_to install src/Alpha.jar
    assert_success
    run pm list-json
    has '"version":"2.0.0"'
    ls backups/plugins/Alpha.jar.backup.*
}

@test "install backs up the plugin's existing configuration" {
    mkdir -p data/plugins/Alpha
    echo "setting: 1" > data/plugins/Alpha/config.yml
    jar Alpha 1.0.0

    run pm install src/Alpha.jar
    assert_success
    has "Backing up existing plugin configuration"
    local saved
    saved="$(ls -d backups/plugins/configs/Alpha.backup.* | head -n 1)"
    [ "$(cat "$saved/config.yml")" = "setting: 1" ]
    # one timestamped copy beside its siblings, and no empty directory left behind
    [ ! -e backups/plugins/configs/Alpha ]
}

@test "install warns about a missing dependency, and answering no cancels" {
    jar Alpha 1.0.0 "depend: Vault"

    run no_to install src/Alpha.jar
    assert_failure
    has "Missing dependencies"
    has "Vault"
    [ ! -f plugins/Alpha.jar ]
}

@test "install is happy when the dependency is already installed" {
    installed Vault 1.7
    jar Alpha 1.0.0 "depend: Vault"

    run pm install src/Alpha.jar
    assert_success
    lacks "Missing dependencies"
    [ -f plugins/Alpha.jar ]
}

@test "dependencies written as a YAML list are understood" {
    installed Vault 1.7
    installed WorldEdit 7.2
    jar Alpha 1.0.0 "depend: [Vault, WorldEdit]"

    run pm install src/Alpha.jar
    assert_success
    lacks "Missing dependencies"
}

@test "a YAML list names only what is actually missing" {
    installed Vault 1.7
    jar Alpha 1.0.0 "depend: [Vault, WorldEdit]"

    run no_to install src/Alpha.jar
    assert_failure
    has "WorldEdit"
    lacks "Vault"
}

@test "quoted dependency names are understood" {
    installed Vault 1.7
    installed WorldEdit 7.2
    jar Alpha 1.0.0 "depend: [\"Vault\", 'WorldEdit']"

    run pm install src/Alpha.jar
    assert_success
    lacks "Missing dependencies"
}

@test "dependencies listed with extra spaces still match" {
    installed Vault 1.7
    jar Alpha 1.0.0 "depend: [ Vault ,  WorldEdit ]"

    run no_to install src/Alpha.jar
    assert_failure
    has "WorldEdit"
    lacks "Vault"
}

@test "dependencies written as a YAML block list are understood" {
    installed Vault 1.7
    jar Alpha 1.0.0 "depend:" "  - Vault" "  - WorldEdit"

    run no_to install src/Alpha.jar
    assert_failure
    has "WorldEdit"
    lacks "Vault"
}

@test "install warns when the plugin's API major version differs from the server's" {
    printf '      - MINECRAFT_VERSION=${MINECRAFT_VERSION:-26.3}\n' > docker-compose.yml
    jar Alpha 1.0.0 "api-version: 1.21"

    run no_to install src/Alpha.jar
    assert_failure
    has "API version mismatch"
    [ ! -f plugins/Alpha.jar ]
}

@test "install does not warn when the API major version matches" {
    printf '      - MINECRAFT_VERSION=${MINECRAFT_VERSION:-1.20.4}\n' > docker-compose.yml
    jar Alpha 1.0.0 "api-version: 1.20"

    run pm install src/Alpha.jar
    assert_success
    lacks "mismatch"
}

# -- disable / enable -----------------------------------------------------------------

@test "disable moves a plugin to disabled/, by name with or without .jar" {
    installed Alpha 1.0.0
    installed Beta 1.0.0

    run pm disable Alpha
    assert_success
    has "Plugin disabled: Alpha.jar"
    run pm disable Beta.jar
    assert_success

    [ -f plugins/disabled/Alpha.jar ]
    [ -f plugins/disabled/Beta.jar ]
    [ ! -f plugins/Alpha.jar ]
}

@test "disable of an unknown plugin fails" {
    run pm disable ghost
    assert_failure
    has "Plugin not found: ghost"
}

@test "disable refuses when a disabled copy already exists" {
    installed Alpha 1.0.0
    mkdir -p plugins/disabled
    cp plugins/Alpha.jar plugins/disabled/Alpha.jar

    run pm disable Alpha
    assert_failure
    has "already disabled"
    [ -f plugins/Alpha.jar ]
}

@test "enable moves a plugin back, by name with or without .jar" {
    mkdir -p plugins/disabled
    make_jar plugins/disabled/Alpha.jar "$(yml Alpha 1.0.0)"
    make_jar plugins/disabled/Beta.jar "$(yml Beta 1.0.0)"

    run pm enable Alpha
    assert_success
    has "Plugin enabled: Alpha.jar"
    run pm enable Beta.jar
    assert_success

    [ -f plugins/Alpha.jar ]
    [ -f plugins/Beta.jar ]
    [ ! -f plugins/disabled/Alpha.jar ]
}

@test "enable of a plugin that is not disabled fails" {
    run pm enable ghost
    assert_failure
    has "not found in disabled directory"
}

@test "enable refuses when an enabled copy already exists" {
    installed Alpha 1.0.0
    mkdir -p plugins/disabled
    cp plugins/Alpha.jar plugins/disabled/Alpha.jar

    run pm enable Alpha
    assert_failure
    has "already enabled"
    [ -f plugins/disabled/Alpha.jar ]
}

# -- remove ---------------------------------------------------------------------------

@test "remove, answering no, keeps the plugin" {
    installed Alpha 1.0.0

    run no_to remove Alpha
    assert_failure
    has "Removal cancelled"
    [ -f plugins/Alpha.jar ]
}

@test "remove, answering yes, deletes the jar and its config after backing the jar up" {
    installed Alpha 1.0.0
    mkdir -p data/plugins/Alpha
    echo "keep?" > data/plugins/Alpha/config.yml

    run yes_to remove Alpha
    assert_success
    has "Plugin removed: Alpha"

    [ ! -f plugins/Alpha.jar ]
    [ ! -d data/plugins/Alpha ]
    ls backups/plugins/Alpha.jar.removed.*
}

@test "remove also finds a disabled plugin" {
    mkdir -p plugins/disabled
    make_jar plugins/disabled/Alpha.jar "$(yml Alpha 1.0.0)"

    run yes_to remove Alpha
    assert_success
    [ ! -f plugins/disabled/Alpha.jar ]
}

@test "remove of an unknown plugin fails" {
    run yes_to remove ghost
    assert_failure
    has "Plugin not found: ghost"
}

@test "remove leaves other plugins' configuration alone" {
    installed Alpha 1.0.0
    mkdir -p data/plugins/Alpha data/plugins/Beta
    echo a > data/plugins/Alpha/config.yml
    echo b > data/plugins/Beta/config.yml

    run yes_to remove Alpha
    assert_success
    [ -f data/plugins/Beta/config.yml ]
}

@test "a jar whose declared name is '..' cannot make remove delete data/" {
    # The config directory to delete comes from the jar's own plugin.yml
    mkdir -p plugins data/plugins
    make_jar plugins/evil.jar "$(yml .. 1.0)"
    mkdir -p data/world
    echo precious > data/world/level.dat

    run yes_to remove evil
    [ "$(cat data/world/level.dat)" = "precious" ]
    [ -d data ]
}

@test "a jar whose declared name contains a slash cannot reach outside data/plugins" {
    mkdir -p plugins data/plugins outside
    echo precious > outside/marker
    make_jar plugins/evil.jar "$(yml ../../outside 1.0)"

    run yes_to remove evil
    [ "$(cat outside/marker)" = "precious" ]
}

@test "plugin names that point outside plugins/ are refused" {
    mkdir -p plugins/disabled outside
    echo precious > outside/Target.jar

    local cmd
    for cmd in disable enable remove; do
        run yes_to "$cmd" ../outside/Target
        assert_failure
        has "Invalid plugin name"
    done
    [ "$(cat outside/Target.jar)" = "precious" ]
}

# -- update -----------------------------------------------------------------------------

@test "update replaces the jar, keeping its filename, and backs up the old jar and config" {
    installed Alpha 1.0.0
    mkdir -p data/plugins/Alpha
    echo "old: setting" > data/plugins/Alpha/config.yml
    jar Alpha 2.0.0

    run pm update Alpha src/Alpha.jar
    assert_success
    has "Old version: 1.0.0"
    has "New version: 2.0.0"
    has "Plugin updated: Alpha"

    run pm list-json
    has '"version":"2.0.0"'
    ls backups/plugins/Alpha.jar.backup.*
    local saved
    saved="$(ls -d backups/plugins/configs/Alpha.backup.* | head -n 1)"
    [ "$(cat "$saved/config.yml")" = "old: setting" ]
    [ ! -e backups/plugins/configs/Alpha ]
}

@test "update needs a new file that exists" {
    installed Alpha 1.0.0

    run pm update Alpha nosuch.jar
    assert_failure
    has "New plugin file not found"
}

@test "update of a plugin that is not installed fails" {
    jar Alpha 2.0.0

    run pm update Alpha src/Alpha.jar
    assert_failure
    has "Plugin not found: Alpha"
}

@test "update warns about an incompatible new version, and answering no cancels" {
    printf '      - MINECRAFT_VERSION=${MINECRAFT_VERSION:-26.3}\n' > docker-compose.yml
    installed Alpha 1.0.0 "api-version: 26.1"
    jar Alpha 2.0.0 "api-version: 1.21"

    run no_to update Alpha src/Alpha.jar
    assert_failure
    has "Update cancelled"
    run pm list-json
    has '"version":"1.0.0"'
}

# -- check-updates ------------------------------------------------------------------------

@test "check-updates lists installed versions" {
    installed Alpha 1.0.0
    installed Beta 2.0.0

    run pm check-updates
    assert_success
    has "Alpha: v1.0.0 (installed)"
    has "Beta: v2.0.0 (installed)"
    has "Checked 2 plugin(s)"
}

@test "check-updates says so when nothing is installed" {
    run pm check-updates
    assert_success
    has "No plugins installed"
}

# -- backup-configs / restore-configs -----------------------------------------------------

@test "backup-configs copies every plugin's configuration" {
    mkdir -p data/plugins/Alpha
    echo a > data/plugins/Alpha/config.yml

    run pm backup-configs
    assert_success
    has "Plugin configurations backed up to"
    local saved
    saved="$(ls -d backups/plugins/configs.* | head -n 1)"
    [ "$(cat "$saved/Alpha/config.yml")" = "a" ]
}

@test "backup-configs with nothing to back up says so" {
    run pm backup-configs
    assert_success
    has "No plugin configurations found"
}

@test "restore-configs needs a path that exists" {
    run pm restore-configs
    assert_failure
    has "Backup path not specified"

    run pm restore-configs /nonexistent/path
    assert_failure
    has "Backup path not found"
}

@test "restore-configs puts the files back, after backing up what is there now" {
    mkdir -p data/plugins/Alpha
    echo current > data/plugins/Alpha/config.yml
    mkdir -p saved/Alpha
    echo restored > saved/Alpha/config.yml

    run pm restore-configs saved
    assert_success
    has "Plugin configurations restored"
    [ "$(cat data/plugins/Alpha/config.yml)" = "restored" ]
    local before
    before="$(ls -d backups/plugins/configs.* | head -n 1)"
    [ "$(cat "$before/Alpha/config.yml")" = "current" ]
}

# -- reload ---------------------------------------------------------------------------------

@test "reload is refused on a vanilla server" {
    SERVER_TYPE=vanilla run pm reload
    assert_failure
    has "Hot-reload not supported"
}

@test "reload says so when the server is not running" {
    run pm reload
    assert_failure
    has "Server is not running"
}

@test "reload sends the command through rcon-cli when the server is running" {
    touch state/running

    run pm reload
    assert_success
    has "Plugins reloaded successfully"
    grep -q "docker exec minecraft-server rcon-cli reload" state/docker-calls
}

@test "reload says what to do when the command could not be sent" {
    touch state/running state/exec-fails

    run pm reload
    assert_failure
    has "Could not send reload command"
}
