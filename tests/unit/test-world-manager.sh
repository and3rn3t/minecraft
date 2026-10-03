#!/usr/bin/env bats
# Unit Tests: world-manager.sh
#
# The script works on directories under data/, config/worlds/ and
# config/world-templates/, edits data/server.properties, and asks docker whether
# the server is running. Everything runs in a throwaway copy of the repo with a
# stubbed docker. The script prompts with `read -n 1`, so confirmations are
# answered through stdin (see yes_to / no_to).

load '../helpers/bats-support/load'
load '../helpers/bats-assert/load'

setup() {
    REPO_DIR="$(cd "$BATS_TEST_DIRNAME/../.." && pwd)"
    TEST_DIR="$(mktemp -d)"
    cp -R "$REPO_DIR/scripts" "$TEST_DIR/scripts"
    mkdir -p "$TEST_DIR/data" "$TEST_DIR/backups" "$TEST_DIR/bin" "$TEST_DIR/state"
    cd "$TEST_DIR" || exit 1

    # docker: `docker ps` lists the server only while state/running exists
    cat > bin/docker <<STUB
#!/bin/bash
echo "docker \$*" >> "$TEST_DIR/state/docker-calls"
if [ "\$1" = "ps" ] && [ -f "$TEST_DIR/state/running" ]; then
    echo "minecraft-server"
fi
exit 0
STUB
    chmod +x bin/docker

    # manage.sh is what switch calls to stop a running server: record the call
    cat > scripts/manage.sh <<STUB
#!/bin/bash
echo "manage.sh \$*" >> "$TEST_DIR/state/manage-calls"
rm -f "$TEST_DIR/state/running"
STUB
    chmod +x scripts/manage.sh

    export PATH="$TEST_DIR/bin:$PATH"
    unset SERVER_PROPERTIES

    cat > data/server.properties <<'PROPS'
level-name=world
level-type=minecraft\:normal
level-seed=
motd=A Minecraft Server
PROPS
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
wm() { "$TEST_DIR/scripts/world-manager.sh" "$@" < /dev/null; }
yes_to() { printf 'y' | "$TEST_DIR/scripts/world-manager.sh" "$@"; }
no_to() { printf 'n' | "$TEST_DIR/scripts/world-manager.sh" "$@"; }

# make_world <name> [region] [nether] [end]
make_world() {
    local name="$1"
    shift
    mkdir -p "$TEST_DIR/data/$name"
    : > "$TEST_DIR/data/$name/level.dat"
    local kind
    for kind in "$@"; do
        case "$kind" in
            region) mkdir -p "$TEST_DIR/data/$name/region" ;;
            nether) mkdir -p "$TEST_DIR/data/$name/DIM-1" ;;
            end) mkdir -p "$TEST_DIR/data/$name/DIM1" ;;
        esac
    done
}

# created_world <name> <type> <seed> [region|nether|end ...]
# `create` first (it refuses, or asks to overwrite, once the world has a
# level.dat), then make it look like a world the server has generated.
created_world() {
    local name="$1" type="$2" seed="$3"
    shift 3
    run wm create "$name" "$type" "$seed"
    [ "$status" -eq 0 ] || { echo "create failed: $output"; return 1; }
    make_world "$name" "$@"
}

prop() { grep "^$1=" "$TEST_DIR/data/server.properties" | cut -d= -f2-; }
# In a Java .properties file "minecraft\:flat" and "minecraft:flat" are the same value
level_type() { prop level-type | tr -d '\\'; }

# -- usage ------------------------------------------------------------------

@test "no command prints usage and exits non-zero" {
    run wm
    assert_failure
    has "Usage:"
    has "list-json"
}

@test "an unknown command prints usage and exits non-zero" {
    run wm frobnicate
    assert_failure
    has "Usage:"
}

# -- list-json (the API consumes this) ---------------------------------------

@test "list-json is an empty array when there are no worlds" {
    run wm list-json
    assert_success
    assert_output "[]"
}

@test "list-json reports each world with its type, and marks the active one" {
    make_world world region
    make_world world_nether nether
    make_world world_the_end end
    make_world world_blank

    run wm list-json
    assert_success

    run python3 - "$output" <<'PY'
import json, sys
worlds = {w["name"]: w for w in json.loads(sys.argv[1])}
assert sorted(worlds) == ["world", "world_blank", "world_nether", "world_the_end"], sorted(worlds)
assert worlds["world"]["type"] == "Overworld"
assert worlds["world_nether"]["type"] == "Nether"
assert worlds["world_the_end"]["type"] == "End"
assert worlds["world_blank"]["type"] == "Unknown"
assert worlds["world"]["active"] is True
assert all(not w["active"] for n, w in worlds.items() if n != "world")
PY
    assert_success
}

@test "list-json ignores directories that have no level.dat" {
    make_world world region
    mkdir -p data/world_empty

    run wm list-json
    assert_success
    lacks "world_empty"
}

@test "list-json stays valid JSON for a world name containing quotes" {
    make_world 'world"quoted' region

    run wm list-json
    assert_success

    run python3 -c 'import json,sys; d=json.loads(sys.argv[1]); assert d[0]["name"]=="world\"quoted", d' "$output"
    assert_success
}

@test "list-json takes the active world from server.properties" {
    make_world world region
    make_world world_two region
    sed -i.bak 's/^level-name=.*/level-name=world_two/' data/server.properties

    run wm list-json
    assert_success

    run python3 - "$output" <<'PY'
import json, sys
active = [w["name"] for w in json.loads(sys.argv[1]) if w["active"]]
assert active == ["world_two"], active
PY
    assert_success
}

@test "a world is listed whatever it is called, not only names starting with 'world'" {
    make_world survival region
    make_world creative-2024 region

    run wm list-json
    assert_success
    has '"name":"survival"'
    has '"name":"creative-2024"'

    run wm list
    assert_success
    has "survival"
    has "creative-2024"
    has "Total: 2 world(s)"
}

@test "the active world is marked even when its name does not start with 'world'" {
    make_world survival region
    sed -i.bak 's/^level-name=.*/level-name=survival/' data/server.properties

    run wm list-json
    assert_success
    has '"name":"survival","size"'
    run python3 - "$output" <<'PY'
import json, sys
active = [w["name"] for w in json.loads(sys.argv[1]) if w["active"]]
assert active == ["survival"], active
PY
    assert_success
}

@test "backups of a replaced world are not listed as worlds" {
    make_world gamma region
    run yes_to create gamma
    assert_success
    ls -d data/gamma.backup.* > /dev/null

    run wm list-json
    assert_success
    lacks "backup"
    run wm list
    lacks "backup"
}

@test "directories under data/ that are not worlds are not listed" {
    make_world survival region
    mkdir -p data/plugins data/logs data/empty
    echo x > data/logs/latest.log

    run wm list-json
    assert_success
    lacks "plugins"
    lacks "logs"
    lacks "empty"
    has '"name":"survival"'
}

# -- list ---------------------------------------------------------------------

@test "list says so when there are no worlds" {
    run wm list
    assert_success
    has "No worlds found"
}

@test "list shows the active world and a total" {
    make_world world region
    make_world world_two region

    run wm list
    assert_success
    has "[ACTIVE]"
    has "world_two"
    has "Total: 2 world(s)"
    has "Current world: world"
}

# -- create -------------------------------------------------------------------

@test "create without a name fails" {
    run wm create
    assert_failure
    has "World name not specified"
}

@test "create rejects names with anything but letters, numbers and underscores" {
    local bad
    for bad in '../escape' 'two words' 'dash-ed' 'dot.ted' 'semi;colon'; do
        run wm create "$bad"
        assert_failure
        has "only letters, numbers, and underscores"
    done
    [ ! -e "$TEST_DIR/escape" ]
    [ -z "$(ls -A data | grep -v server.properties)" ]
}

@test "create makes the world directory and a config recording type and seed" {
    run wm create alpha flat 12345
    assert_success
    has "World created: alpha"

    [ -d data/alpha ]
    run cat config/worlds/alpha.conf
    has "WORLD_NAME=alpha"
    has "WORLD_TYPE=flat"
    has "WORLD_SEED=12345"
}

@test "create defaults the type to normal" {
    run wm create beta
    assert_success
    run cat config/worlds/beta.conf
    has "WORLD_TYPE=normal"
}

@test "create over an existing world, answering no, leaves it alone" {
    make_world gamma region
    echo keep > data/gamma/marker

    run no_to create gamma
    assert_failure
    has "Creation cancelled"
    [ "$(cat data/gamma/marker)" = "keep" ]
}

@test "create over an existing world, answering yes, backs the old one up first" {
    make_world gamma region
    echo keep > data/gamma/marker

    run yes_to create gamma
    assert_success
    has "backed up to: gamma.backup."

    local backup
    backup="$(ls -d data/gamma.backup.* | head -n 1)"
    [ "$(cat "$backup/marker")" = "keep" ]
    [ -d data/gamma ]
    [ ! -e data/gamma/marker ]
}

# -- config and seeds ----------------------------------------------------------

@test "a text seed containing spaces survives into server.properties" {
    run wm create textseed normal "hello world"
    assert_success

    run wm config textseed
    assert_success
    [ "$(prop level-seed)" = "hello world" ]
}

@test "a seed holding shell syntax is stored as text and never executed" {
    run wm create evil normal 'x; touch /tmp/world-manager-pwned-$$; y'
    assert_success

    run wm config evil
    rm -f /tmp/world-manager-pwned-*
    [ ! -e "/tmp/world-manager-pwned-$$" ]
}

@test "a seed containing sed metacharacters is written literally" {
    run wm create slashes normal 'a/b&c'
    assert_success

    run wm config slashes
    assert_success
    [ "$(prop level-seed)" = 'a/b&c' ]
}

@test "create refuses a seed or type containing a line break or other control character" {
    local bad
    for bad in $'1\nonline-mode=false' $'1\ronline-mode=false' $'tab\tseed'; do
        run wm create inj normal "$bad"
        assert_failure
        has "control characters"
        run wm create inj "$bad"
        assert_failure
    done
    [ ! -e config/worlds/inj.conf ]
    [ ! -e data/inj ]
}

@test "extra lines in a config file never reach server.properties" {
    # A config edited by hand (or written before create refused line breaks)
    make_world multiline region
    mkdir -p config/worlds
    printf 'WORLD_NAME=multiline\nWORLD_TYPE=normal\nWORLD_SEED=1\nonline-mode=false\n' > config/worlds/multiline.conf

    run wm config multiline
    assert_success
    [ "$(prop level-seed)" = "1" ]
    [ -z "$(prop online-mode)" ]
}

@test "a seed is appended to server.properties as exactly one line" {
    sed -i.bak '/^level-seed=/d' data/server.properties
    run wm create oneline normal -n
    assert_success

    run wm config oneline
    assert_success
    [ "$(grep -c '^level-seed=' data/server.properties)" = "1" ]
    [ "$(prop level-seed)" = "-n" ]
}

@test "config applies the world type to level-type" {
    local type expected
    for type in flat amplified large_biomes normal; do
        run wm create "t_$type" "$type"
        assert_success
        run wm config "t_$type"
        assert_success
        [ "$(level_type)" = "minecraft:$type" ]
    done
}

@test "config adds level-seed when server.properties has none" {
    sed -i.bak '/^level-seed=/d' data/server.properties
    run wm create seeded normal 999
    assert_success

    run wm config seeded
    assert_success
    [ "$(prop level-seed)" = "999" ]
}

@test "config for a world with no config file creates a default one" {
    make_world fresh region

    run wm config fresh
    assert_success
    has "Creating default configuration"
    [ -f config/worlds/fresh.conf ]
}

@test "config leaves no .bak files behind" {
    run wm create tidy flat 5
    assert_success
    run wm config tidy
    assert_success
    [ -z "$(ls data | grep '\.bak$')" ]
}

# -- switch ---------------------------------------------------------------------

@test "switch without a name fails" {
    run wm switch
    assert_failure
    has "World name not specified"
}

@test "switching to the active world does nothing" {
    run wm switch world
    assert_success
    has "Already using world: world"
}

@test "switch updates level-name in server.properties and keeps the other settings" {
    make_world other region

    run wm switch other
    assert_success
    has "Switched to world: other"
    [ "$(prop level-name)" = "other" ]
    [ "$(prop motd)" = "A Minecraft Server" ]
}

@test "switch applies the target world's own configuration" {
    created_world flatland flat 42 region

    run wm switch flatland
    assert_success
    [ "$(prop level-name)" = "flatland" ]
    [ "$(level_type)" = "minecraft:flat" ]
    [ "$(prop level-seed)" = "42" ]
}

@test "switch adds level-name when server.properties lacks it" {
    sed -i.bak '/^level-name=/d' data/server.properties
    make_world other region

    run wm switch other
    assert_success
    [ "$(prop level-name)" = "other" ]
}

@test "switch to a world that does not exist, answering no, changes nothing" {
    run no_to switch ghost
    assert_failure
    has "Switch cancelled"
    [ "$(prop level-name)" = "world" ]
}

@test "switch to a world that does not exist, answering yes, creates it first" {
    run yes_to switch newworld
    assert_success
    [ -d data/newworld ]
    [ -f config/worlds/newworld.conf ]
    [ "$(prop level-name)" = "newworld" ]
}

@test "switch stops a running server before editing server.properties" {
    make_world other region
    touch state/running

    run wm switch other
    assert_success
    has "Stopping to switch worlds"
    grep -q "manage.sh stop" state/manage-calls
    [ "$(prop level-name)" = "other" ]
}

@test "switch does not touch the server when it is not running" {
    make_world other region

    run wm switch other
    assert_success
    [ ! -f state/manage-calls ]
}

@test "switch fails cleanly when server.properties is missing" {
    make_world other region
    rm data/server.properties

    run wm switch other
    assert_failure
    has "server.properties not found"
}

@test "switch honours SERVER_PROPERTIES from the environment" {
    make_world other region
    cp data/server.properties alt.properties

    SERVER_PROPERTIES="$TEST_DIR/alt.properties" run wm switch other
    assert_success
    grep -q '^level-name=other$' alt.properties
    grep -q '^level-name=world$' data/server.properties
}

@test "switch writes a world name containing sed metacharacters literally" {
    mkdir -p "data/a&b"
    : > "data/a&b/level.dat"

    run wm switch 'a&b'
    assert_success
    [ "$(prop level-name)" = 'a&b' ]
}

# -- delete ---------------------------------------------------------------------

@test "delete without a name fails" {
    run wm delete
    assert_failure
    has "World name not specified"
}

@test "delete refuses the active world" {
    make_world world region

    run yes_to delete world
    assert_failure
    has "Cannot delete the active world"
    [ -d data/world ]
}

@test "delete reports a world that does not exist" {
    run yes_to delete ghost
    assert_failure
    has "World not found: ghost"
}

@test "delete, answering no, keeps the world" {
    make_world doomed region

    run no_to delete doomed
    assert_failure
    has "Deletion cancelled"
    [ -d data/doomed ]
}

@test "delete, answering yes, removes the world and its config after backing it up" {
    make_world doomed region
    echo precious > data/doomed/marker
    run wm create doomed
    run yes_to delete doomed
    assert_success
    has "World deleted: doomed"

    [ ! -e data/doomed ]
    [ ! -e config/worlds/doomed.conf ]

    local archive
    archive="$(ls backups/doomed.deleted.*.tar.gz | head -n 1)"
    run tar -xzOf "$archive" doomed/marker
    assert_output "precious"
}

@test "delete does not remove the world when its backup could not be written" {
    make_world doomed region
    rm -rf backups
    : > backups # a file where the directory should be: the archive cannot be written

    run yes_to delete doomed
    assert_failure
    [ -d data/doomed ]
    lacks "World deleted"
}

@test "config on an existing world with no config file never moves the world aside" {
    # Worlds the server generated itself have no config. config used to go
    # through create, which asks "Overwrite?" and, on yes, moves the world away.
    make_world fresh region
    echo precious > data/fresh/marker

    run yes_to config fresh
    assert_success
    [ "$(cat data/fresh/marker)" = "precious" ]
    [ -z "$(ls -d data/fresh.backup.* 2>/dev/null)" ]
    [ -f config/worlds/fresh.conf ]
}

@test "switching to a world the server generated itself works without prompting" {
    make_world generated region
    echo precious > data/generated/marker

    run wm switch generated
    assert_success
    [ "$(prop level-name)" = "generated" ]
    [ "$(cat data/generated/marker)" = "precious" ]
}

@test "a config written by create is plain data: its date line does not break reading it" {
    run wm create dated flat 3
    assert_success
    grep -qE '^CREATED=[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9:]{8}$' config/worlds/dated.conf

    run wm config dated
    assert_success
    lacks "command not found"
    has "World configuration applied: dated"
}

@test "a config file is never executed" {
    make_world sneaky region
    mkdir -p config/worlds
    cat > config/worlds/sneaky.conf <<CONF
WORLD_NAME=sneaky
WORLD_TYPE=normal
WORLD_SEED=
touch $TEST_DIR/state/executed
CONF

    run wm config sneaky
    [ ! -e state/executed ]
}

# -- names that could leave data/ -----------------------------------------------

@test "commands refuse a world name that points outside data/" {
    # A decoy that looks like a world, outside data/: the old code would have
    # deleted, backed up or read it.
    mkdir -p outside
    : > outside/level.dat
    echo precious > outside/marker

    local cmd
    for cmd in delete info backup config switch; do
        run yes_to "$cmd" ../outside
        assert_failure
        has "Invalid world name"
    done
    [ "$(cat outside/marker)" = "precious" ]
    [ -z "$(ls backups)" ]
}

@test "templates refuse names that point outside their directories" {
    make_world world region
    mkdir -p outside
    : > outside/level.dat

    run wm create-template ../mold world
    assert_failure
    has "Invalid template name"

    run wm create-template mold ../outside
    assert_failure
    has "Invalid world name"

    run wm from-template ../escape mold
    assert_failure
    has "Invalid world name"

    run wm from-template fresh ../mold
    assert_failure
    has "Invalid template name"
    [ ! -e escape ]
}

@test "names with hyphens and dots are still accepted for worlds that already exist" {
    make_world survival-2024.1 region

    run wm switch survival-2024.1
    assert_success
    [ "$(prop level-name)" = "survival-2024.1" ]
}

# -- info -----------------------------------------------------------------------

@test "info defaults to the active world" {
    make_world world region
    : > data/world/region/r.0.0.mca

    run wm info
    assert_success
    has "World Information: world"
    has "Type: Overworld"
    has "Regions: 1"
    has "Status: ACTIVE"
}

@test "info reports dimensions and the world's configuration" {
    created_world world_two flat 77 region nether end

    run wm info world_two
    assert_success
    has "Nether: Yes"
    has "End: Yes"
    has "WORLD_TYPE: flat"
    has "WORLD_SEED: 77"
    lacks "Status: ACTIVE"
}

@test "info on a missing world fails" {
    run wm info ghost
    assert_failure
    has "World not found: ghost"
}

# -- backup ---------------------------------------------------------------------

@test "backup archives the named world" {
    make_world world_two region
    echo data > data/world_two/marker

    run wm backup world_two
    assert_success
    has "World backed up"

    local archive
    archive="$(ls backups/world_world_two_*.tar.gz | head -n 1)"
    run tar -xzOf "$archive" world_two/marker
    assert_output "data"
}

@test "backup defaults to the active world" {
    make_world world region

    run wm backup
    assert_success
    ls backups/world_world_*.tar.gz
}

@test "backup of a missing world fails and writes nothing" {
    run wm backup ghost
    assert_failure
    has "World not found: ghost"
    [ -z "$(ls -A backups)" ]
}

# -- sizes ----------------------------------------------------------------------

@test "sizes says so when there are no worlds" {
    du -sb "$TEST_DIR" > /dev/null 2>&1 || skip "needs GNU du (-b); the Pi and CI have it, macOS does not"

    run wm sizes
    assert_success
    has "No worlds found"
}

@test "sizes lists each world and a total" {
    du -sb "$TEST_DIR" > /dev/null 2>&1 || skip "needs GNU du (-b); the Pi and CI have it, macOS does not"
    make_world world region
    make_world survival region

    run wm sizes
    assert_success
    has "survival"
    has "Total: 2 world(s)"
}

# -- templates ------------------------------------------------------------------

@test "create-template without a name fails" {
    run wm create-template
    assert_failure
    has "Template name not specified"
}

@test "create-template from a missing world fails" {
    run wm create-template mold ghost
    assert_failure
    has "Source world not found: ghost"
}

@test "a template leaves out player data, and a world built from it is clean" {
    created_world world flat 5 region
    mkdir -p data/world/playerdata data/world/stats data/world/advancements
    echo me > data/world/playerdata/uuid.dat
    echo blocks > data/world/region/r.0.0.mca

    run wm create-template mold world
    assert_success
    has "Template created: mold"

    run wm from-template world_copy mold
    assert_success
    has "World created from template: world_copy"

    [ -f data/world_copy/level.dat ]
    [ "$(cat data/world_copy/region/r.0.0.mca)" = "blocks" ]
    [ ! -e data/world_copy/playerdata ]
    [ ! -e data/world_copy/stats ]
    [ ! -e data/world_copy/advancements ]
}

@test "without rsync the template still leaves player data out" {
    # create-template falls back to tar when rsync fails or is missing
    printf '#!/bin/bash\nexit 1\n' > bin/rsync
    chmod +x bin/rsync
    created_world world flat 5 region
    mkdir -p data/world/playerdata data/world/stats data/world/advancements
    echo me > data/world/playerdata/uuid.dat
    echo blocks > data/world/region/r.0.0.mca

    run wm create-template mold world
    assert_success

    run wm from-template world_copy mold
    assert_success
    [ "$(cat data/world_copy/region/r.0.0.mca)" = "blocks" ]
    [ ! -e data/world_copy/playerdata ]
    [ ! -e data/world_copy/stats ]
    [ ! -e data/world_copy/advancements ]
}

@test "from-template carries the config over under the new world's name" {
    created_world world flat 5 region
    run wm create-template mold world
    assert_success

    run wm from-template world_copy mold
    assert_success
    run cat config/worlds/world_copy.conf
    has "WORLD_NAME=world_copy"
    has "WORLD_TYPE=flat"
    lacks "WORLD_NAME=world"$'\n'
}

@test "from-template needs both a world name and a template" {
    run wm from-template onlyone
    assert_failure
    has "World name and template name required"
}

@test "from-template reports a missing template" {
    run wm from-template fresh nosuchtemplate
    assert_failure
    has "Template not found: nosuchtemplate"
}

@test "from-template over an existing world, answering no, leaves it alone" {
    make_world world region
    run wm create-template mold world
    make_world target region
    echo keep > data/target/marker

    run no_to from-template target mold
    assert_failure
    has "Creation cancelled"
    [ "$(cat data/target/marker)" = "keep" ]
}
