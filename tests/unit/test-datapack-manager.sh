#!/usr/bin/env bats
# Unit tests for datapack-manager.sh

load '../helpers/bats-support/load'
load '../helpers/bats-assert/load'

REPO_ROOT="$(cd "$(dirname "${BATS_TEST_FILENAME}")/../.." && pwd)"

setup() {
    TEST_DIR="$(mktemp -d)"
    cd "$TEST_DIR" || exit 1

    mkdir -p scripts data config
    cp "${REPO_ROOT}/scripts/datapack-manager.sh" scripts/
    cp -r "${REPO_ROOT}/scripts/lib" scripts/
    chmod +x scripts/datapack-manager.sh

    # A stub in place of the real rcon-client.sh, so enable/disable/reload can
    # run to completion without a live server. Records that it was called so
    # tests can assert on it.
    cat > scripts/rcon-client.sh <<'EOF'
#!/bin/bash
echo "$@" >> "$(dirname "$0")/../rcon-calls.log"
echo "reload stub ok"
EOF
    chmod +x scripts/rcon-client.sh

    # The real path: data/server.properties, matching
    # server-properties-manager.sh and performance-presets.sh. A repo-root
    # server.properties (what this script used to read) must NOT be enough
    # on its own -- see "reads the runtime server.properties, not a
    # repo-root one" below.
    echo "level-name=world" > data/server.properties
    mkdir -p data/world
}

teardown() {
    rm -rf "$TEST_DIR"
}

@test "datapack-manager create scaffolds pack.mcmeta and advancements/functions dirs" {
    run scripts/datapack-manager.sh create family
    assert_success

    assert_file_exists "config/datapacks/family/pack.mcmeta"
    assert_dir_exists "config/datapacks/family/data/family/advancements"
    assert_dir_exists "config/datapacks/family/data/family/functions"
}

@test "datapack-manager create rejects a name with spaces" {
    run scripts/datapack-manager.sh create "not valid"
    assert_failure
}

@test "datapack-manager create refuses to overwrite an existing datapack" {
    scripts/datapack-manager.sh create family
    run scripts/datapack-manager.sh create family
    assert_failure
    assert_line "already exists"
}

@test "datapack-manager install rejects loopback/private URLs, including IPv6 and userinfo bypasses" {
    for url in \
        "http://example.com/x.zip" \
        "https://127.0.0.1/x.zip" \
        "https://[::1]/x.zip" \
        "https://evil@127.0.0.1/x.zip" \
        "https://[fe80::1]/x.zip" \
        "https://192.168.1.5/x.zip" \
        "https://myserver.local/x.zip"; do
        run scripts/datapack-manager.sh install family --url "$url" --yes
        assert_failure
    done
}

@test "datapack-manager install rejects a zip with a path-traversal entry" {
    mkdir -p evil/sneaky
    (cd evil && echo '{"pack":{"pack_format":26,"description":"evil"}}' > pack.mcmeta && zip -q evil.zip pack.mcmeta)
    python3 -c "
import zipfile
with zipfile.ZipFile('evil/evil.zip', 'a') as z:
    z.writestr('../../../tmp/pwned.txt', 'pwned')
"

    run scripts/datapack-manager.sh install evil --file evil/evil.zip --yes
    assert_failure
    assert_line "unsafe path in archive"
    [ ! -f "/tmp/pwned.txt" ]
}

@test "datapack-manager install leaves the existing pack untouched when the replacement archive is invalid" {
    scripts/datapack-manager.sh create family
    echo "ORIGINAL_MARKER" > config/datapacks/family/marker.txt
    echo "not a real zip" > bad.zip

    run scripts/datapack-manager.sh install family --file bad.zip --yes
    assert_failure

    run cat config/datapacks/family/marker.txt
    assert_output "ORIGINAL_MARKER"
}

@test "datapack-manager delete aborts without deleting when the backup fails" {
    scripts/datapack-manager.sh create family
    mkdir -p backups
    chmod 555 backups

    run scripts/datapack-manager.sh delete family --yes
    assert_failure

    chmod 755 backups
    assert_dir_exists "config/datapacks/family"
}

@test "datapack-manager list-json emits valid, parseable JSON" {
    scripts/datapack-manager.sh create family
    run scripts/datapack-manager.sh list-json
    assert_success
    echo "$output" | python3 -c "import json,sys; data=json.load(sys.stdin); assert isinstance(data, list)"
}

@test "datapack-manager list-json reports enabled=false before enable, true after" {
    scripts/datapack-manager.sh create family
    run scripts/datapack-manager.sh list-json
    assert_line '"enabled":false'

    scripts/datapack-manager.sh enable family

    run scripts/datapack-manager.sh list-json
    assert_line '"enabled":true'
}

@test "datapack-manager validate passes on a freshly created datapack" {
    scripts/datapack-manager.sh create family
    run scripts/datapack-manager.sh validate family
    assert_success
    assert_line "PASS"
}

@test "datapack-manager validate fails on broken JSON" {
    scripts/datapack-manager.sh create family
    echo '{not valid json' > config/datapacks/family/data/family/advancements/broken.json

    run scripts/datapack-manager.sh validate family
    assert_failure
    assert_line "FAIL"
    assert_line "broken.json"
}

@test "datapack-manager enable copies the tracked source into the current world and reloads" {
    scripts/datapack-manager.sh create family
    run scripts/datapack-manager.sh enable family
    assert_success

    assert_file_exists "data/world/datapacks/family/pack.mcmeta"
    assert_line "Reloading datapacks"
    assert_file_contains "rcon-calls.log" "reload"
}

@test "datapack-manager disable removes the deployed copy but keeps the tracked source" {
    scripts/datapack-manager.sh create family
    scripts/datapack-manager.sh enable family

    run scripts/datapack-manager.sh disable family
    assert_success

    [ ! -d "data/world/datapacks/family" ]
    assert_file_exists "config/datapacks/family/pack.mcmeta"
}

@test "datapack-manager disable errors when the datapack was never enabled" {
    scripts/datapack-manager.sh create family
    run scripts/datapack-manager.sh disable family
    assert_failure
    assert_line "not enabled"
}

@test "datapack-manager delete --yes backs up and removes the tracked source" {
    scripts/datapack-manager.sh create family
    run scripts/datapack-manager.sh delete family --yes
    assert_success

    [ ! -d "config/datapacks/family" ]
    run bash -c "ls backups/datapack-family-*.tar.gz"
    assert_success
}

@test "datapack-manager reads the runtime server.properties, not a repo-root one" {
    echo "level-name=custom_world" > data/server.properties
    mkdir -p data/custom_world
    # A stale/decoy repo-root file must be ignored, not preferred.
    echo "level-name=world" > server.properties

    scripts/datapack-manager.sh create family
    run scripts/datapack-manager.sh list-json
    assert_line '"world":"custom_world"'
}

@test "datapack-manager with no arguments prints usage and exits nonzero" {
    run scripts/datapack-manager.sh
    assert_failure
    assert_line "Usage:"
}
