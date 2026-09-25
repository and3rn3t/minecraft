#!/bin/bash
# Datapack Manager for Minecraft Server
#
# Datapacks are plain JSON, work on vanilla, and hot-reload with /reload — no
# plugin required (docs/ROADMAP.md, "F3. A datapack pipeline"). The canonical
# source of each datapack lives under config/datapacks/<name>/, which is
# tracked in git, so a bad change is one `git revert` away. `enable` copies
# that source into data/<world>/datapacks/<name>/, which is where the running
# server actually reads datapacks from and which is gitignored (it's the
# Pi's runtime state). `disable` removes the deployed copy only — the
# tracked source is never touched by enable/disable.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source-path=SCRIPTDIR
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

DATAPACKS_SRC_DIR="${PROJECT_DIR}/config/datapacks"
DATA_DIR="${PROJECT_DIR}/data"
SERVER_PROPERTIES="${PROJECT_DIR}/server.properties"
BACKUPS_DIR="${PROJECT_DIR}/backups"

mkdir -p "$DATAPACKS_SRC_DIR"

# The pack_format datapacks built by this pipeline target. 26 is the format
# introduced in 1.20.3/1.20.4, the version this project targets (docs/ROADMAP.md
# legend: "vanilla 1.20.4").
PACK_FORMAT=26

# Which world's datapacks directory enable/disable/reload act on. Duplicated
# from world-manager.sh's get_current_world() rather than sourced from it:
# that script has its own mkdir side effects on load and isn't meant to be
# used as a library.
#
# Falls back to "world" whenever the file is missing, has no level-name=
# line, or the line has no value -- not just when the file is missing. A
# bare `grep | cut | tr || echo "world"` doesn't cover the middle case: with
# no `pipefail`, `||` sees tr's exit status, and tr succeeds (producing
# empty output) even when grep matched nothing upstream.
get_current_world() {
    local world_name=""
    if [ -f "$SERVER_PROPERTIES" ]; then
        world_name=$(grep -E "^level-name=" "$SERVER_PROPERTIES" | cut -d'=' -f2 | tr -d '\r')
    fi
    echo "${world_name:-world}"
}

# Escape backslashes and double quotes for embedding in a JSON string.
_json_escape() {
    printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g'
}

_validate_name() {
    local name="$1"
    if [ -z "$name" ]; then
        log_error "Error: datapack name not specified"
        return 1
    fi
    if [[ ! "$name" =~ ^[a-zA-Z0-9_]+$ ]]; then
        log_error "Error: datapack name must contain only letters, numbers, and underscores"
        return 1
    fi
    return 0
}

create_datapack() {
    local name="$1"
    _validate_name "$name" || return 1

    local pack_dir="${DATAPACKS_SRC_DIR}/${name}"
    if [ -d "$pack_dir" ]; then
        log_error "Error: datapack already exists: $name"
        return 1
    fi

    mkdir -p "${pack_dir}/data/${name}/advancement"
    mkdir -p "${pack_dir}/data/${name}/function"
    mkdir -p "${pack_dir}/data/${name}/loot_table"
    mkdir -p "${pack_dir}/data/${name}/recipe"

    cat > "${pack_dir}/pack.mcmeta" <<EOF
{
    "pack": {
        "pack_format": ${PACK_FORMAT},
        "description": "${name} datapack"
    }
}
EOF

    log_success "Created datapack source: config/datapacks/${name}"
    log_info "Add advancements, functions, loot tables etc. under data/${name}/, then run:"
    log_info "  $0 enable ${name}"
}

list_datapacks() {
    log_info "Datapacks:"
    echo ""

    local current_world
    current_world=$(get_current_world)
    local deployed_dir="${DATA_DIR}/${current_world}/datapacks"
    local count=0

    for pack_dir in "$DATAPACKS_SRC_DIR"/*/; do
        [ -d "$pack_dir" ] || continue
        local name
        name=$(basename "$pack_dir")
        count=$((count + 1))

        if [ -d "${deployed_dir}/${name}" ]; then
            echo -e "  ${GREEN}✓${NC} ${GREEN}[ENABLED]${NC} $name"
        else
            echo -e "  ${BLUE}○${NC} [available] $name"
        fi
    done

    if [ "$count" -eq 0 ]; then
        log_warn "  No datapacks found. Create one with: $0 create <name>"
    else
        echo ""
        log_info "Current world: $current_world"
    fi
}

list_datapacks_json() {
    local current_world
    current_world=$(get_current_world)
    local deployed_dir="${DATA_DIR}/${current_world}/datapacks"

    local entries=()
    for pack_dir in "$DATAPACKS_SRC_DIR"/*/; do
        [ -d "$pack_dir" ] || continue
        local name
        name=$(basename "$pack_dir")
        local enabled="false"
        [ -d "${deployed_dir}/${name}" ] && enabled="true"

        entries+=("$(printf '{"name":"%s","enabled":%s,"world":"%s"}' \
            "$(_json_escape "$name")" "$enabled" "$(_json_escape "$current_world")")")
    done

    local IFS=,
    echo "[${entries[*]}]"
}

enable_datapack() {
    local name="$1"
    _validate_name "$name" || return 1

    local source_dir="${DATAPACKS_SRC_DIR}/${name}"
    if [ ! -d "$source_dir" ]; then
        log_error "Error: no such datapack: $name (looked in config/datapacks/${name})"
        return 1
    fi
    if [ ! -f "${source_dir}/pack.mcmeta" ]; then
        log_error "Error: ${name} has no pack.mcmeta; run '$0 validate ${name}' for details"
        return 1
    fi

    local current_world
    current_world=$(get_current_world)
    local target_dir="${DATA_DIR}/${current_world}/datapacks/${name}"

    mkdir -p "$(dirname "$target_dir")"
    rm -rf "$target_dir"
    cp -r "$source_dir" "$target_dir"

    log_success "Enabled datapack: $name (world: $current_world)"
    reload_datapacks
}

disable_datapack() {
    local name="$1"
    _validate_name "$name" || return 1

    local current_world
    current_world=$(get_current_world)
    local target_dir="${DATA_DIR}/${current_world}/datapacks/${name}"

    if [ ! -d "$target_dir" ]; then
        log_error "Error: ${name} is not enabled in world ${current_world}"
        return 1
    fi

    rm -rf "$target_dir"
    log_success "Disabled datapack: $name (world: $current_world)"
    log_info "Tracked source at config/datapacks/${name} was not touched."
    reload_datapacks
}

# Download a file with whichever of curl/wget is available. Mirrors
# mod-pack-installer.sh's download_file().
_download_file() {
    local url="$1"
    local output="$2"

    if command -v curl >/dev/null 2>&1; then
        curl -fsSL -o "$output" "$url"
    elif command -v wget >/dev/null 2>&1; then
        wget -q -O "$output" "$url"
    else
        log_error "Error: curl or wget required for downloads"
        return 1
    fi
}

install_datapack() {
    local name="$1"
    shift
    _validate_name "$name" || return 1

    local url=""
    local file=""
    local auto_yes="false"
    while [ $# -gt 0 ]; do
        case "$1" in
            --url)
                url="$2"
                shift 2
                ;;
            --file)
                file="$2"
                shift 2
                ;;
            --yes)
                auto_yes="true"
                shift
                ;;
            *)
                log_error "Error: unknown option: $1"
                return 1
                ;;
        esac
    done

    if [ -z "$url" ] && [ -z "$file" ]; then
        log_error "Error: install needs --url <url> or --file <path>"
        return 1
    fi

    local pack_dir="${DATAPACKS_SRC_DIR}/${name}"
    if [ -d "$pack_dir" ]; then
        log_warn "Datapack already exists: $name"
        if [ "$auto_yes" = "true" ]; then
            REPLY="y"
        else
            read -p "Overwrite? (y/N): " -n 1 -r
            echo
        fi
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_warn "Install cancelled"
            return 1
        fi
        rm -rf "$pack_dir"
    fi

    local zip_path="$file"
    local tmp_download=""
    if [ -n "$url" ]; then
        tmp_download="$(mktemp)-datapack.zip"
        log_info "Downloading $url"
        if ! _download_file "$url" "$tmp_download"; then
            rm -f "$tmp_download"
            return 1
        fi
        zip_path="$tmp_download"
    fi

    if [ ! -f "$zip_path" ]; then
        log_error "Error: file not found: $zip_path"
        [ -n "$tmp_download" ] && rm -f "$tmp_download"
        return 1
    fi

    mkdir -p "$pack_dir"
    if ! unzip -q -o "$zip_path" -d "$pack_dir"; then
        log_error "Error: failed to extract $zip_path"
        rm -rf "$pack_dir"
        [ -n "$tmp_download" ] && rm -f "$tmp_download"
        return 1
    fi
    [ -n "$tmp_download" ] && rm -f "$tmp_download"

    if [ ! -f "${pack_dir}/pack.mcmeta" ]; then
        log_error "Error: extracted archive has no pack.mcmeta at its root"
        rm -rf "$pack_dir"
        return 1
    fi

    log_success "Installed datapack source: config/datapacks/${name}"
    enable_datapack "$name"
}

validate_datapack() {
    local name="$1"
    _validate_name "$name" || return 1

    local pack_dir="${DATAPACKS_SRC_DIR}/${name}"
    if [ ! -d "$pack_dir" ]; then
        log_error "Error: no such datapack: $name"
        return 1
    fi

    python3 - "$pack_dir" <<'EOF'
import json
import sys
from pathlib import Path

pack_dir = Path(sys.argv[1])
errors = []

mcmeta = pack_dir / "pack.mcmeta"
if not mcmeta.is_file():
    errors.append("missing pack.mcmeta")
else:
    try:
        json.loads(mcmeta.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"pack.mcmeta: invalid JSON: {exc}")

checked = 0
for path in pack_dir.rglob("*.json"):
    checked += 1
    try:
        json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"{path.relative_to(pack_dir)}: invalid JSON: {exc}")

if errors:
    for error in errors:
        print(f"FAIL: {error}")
    sys.exit(1)

print(f"PASS: pack.mcmeta valid, {checked} other JSON file(s) valid")
EOF
}

delete_datapack() {
    local name="$1"
    local auto_yes="${2:-}"
    _validate_name "$name" || return 1

    local pack_dir="${DATAPACKS_SRC_DIR}/${name}"
    if [ ! -d "$pack_dir" ]; then
        log_error "Error: no such datapack: $name"
        return 1
    fi

    log_warn "This deletes the tracked source at config/datapacks/${name}."
    if [ "$auto_yes" = "--yes" ]; then
        REPLY="y"
    else
        read -p "Are you sure? (y/N): " -n 1 -r
        echo
    fi
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_warn "Delete cancelled"
        return 1
    fi

    mkdir -p "$BACKUPS_DIR"
    local backup_name
    backup_name="datapack-${name}-$(date +%Y%m%d-%H%M%S)"
    tar -czf "${BACKUPS_DIR}/${backup_name}.tar.gz" -C "$DATAPACKS_SRC_DIR" "$name" 2>/dev/null || true
    log_info "Backed up to backups/${backup_name}.tar.gz"

    local current_world
    current_world=$(get_current_world)
    local target_dir="${DATA_DIR}/${current_world}/datapacks/${name}"
    if [ -d "$target_dir" ]; then
        rm -rf "$target_dir"
        reload_datapacks
    fi

    rm -rf "$pack_dir"
    log_success "Deleted datapack: $name"
}

reload_datapacks() {
    log_info "Reloading datapacks..."
    "${SCRIPT_DIR}/rcon-client.sh" command reload
}

usage() {
    echo "Datapack Manager for Minecraft Server"
    echo ""
    echo "Usage: $0 <command> [options]"
    echo ""
    echo "Commands:"
    echo "  create <name>                  - Scaffold a new datapack under config/datapacks/"
    echo "  list                           - List datapacks (enabled/available)"
    echo "  list-json                      - Machine-readable listing"
    echo "  install <name> --url <url>     - Download and install a datapack from a zip URL"
    echo "  install <name> --file <path>   - Install a datapack from a local zip file"
    echo "  enable <name>                  - Deploy a datapack into the current world and reload"
    echo "  disable <name>                 - Remove a datapack from the current world and reload"
    echo "  validate <name>                - Check pack.mcmeta and JSON syntax"
    echo "  delete <name> [--yes]          - Back up and delete a datapack's tracked source"
    echo "  reload                         - Run /reload on the running server"
    echo ""
    echo "  --yes skips the interactive confirmation on install (overwrite) and delete."
    echo ""
    exit 1
}

main() {
    case "${1:-}" in
        create)
            create_datapack "$2"
            ;;
        list)
            list_datapacks
            ;;
        list-json)
            list_datapacks_json
            ;;
        install)
            install_datapack "$2" "${@:3}"
            ;;
        enable)
            enable_datapack "$2"
            ;;
        disable)
            disable_datapack "$2"
            ;;
        validate)
            validate_datapack "$2"
            ;;
        delete)
            delete_datapack "$2" "$3"
            ;;
        reload)
            reload_datapacks
            ;;
        *)
            usage
            ;;
    esac
}

main "$@"
