#!/bin/bash
# Keep the game address's SRV record pointed at the playit.gg tunnel
#
# The home connection is behind CGNAT, so players reach the server through a
# playit.gg tunnel rather than a port forward (docs/PLAYIT.md). Players type
# the family's own hostname; a Cloudflare SRV record on it names the tunnel's
# host and port. playit can move the tunnel to a new port without warning --
# it did once, from 33856 to 33903 -- and the family hostname then silently
# stops working.
#
# playit publishes the tunnel's current host and port as an SRV record on its
# own hostname. This script reads that record and copies the host and port
# into the Cloudflare record whenever they differ. It never creates or deletes
# a record, and never writes anything it could not first validate.
#
# Usage: playit-srv-sync.sh {check|sync}
#   check  Report whether the records match. Exits 1 when they don't.
#   sync   Update the Cloudflare record when they don't match.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source-path=SCRIPTDIR
# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

PLAYIT_CONFIG="${PLAYIT_CONFIG:-${PROJECT_DIR}/config/playit.conf}"
DOH_URL="${DOH_URL:-https://cloudflare-dns.com/dns-query}"
CF_API="${CF_API:-https://api.cloudflare.com/client/v4}"

usage() {
    sed -n '/^# Usage:/,/^$/p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
}

load_config() {
    if [ ! -f "$PLAYIT_CONFIG" ]; then
        log_error "Config not found: $PLAYIT_CONFIG (copy config/playit.conf.example)"
        exit 2
    fi
    # shellcheck source=/dev/null
    source "$PLAYIT_CONFIG"
    local missing=()
    for var in PLAYIT_HOST GAME_SRV_NAME CLOUDFLARE_API_TOKEN CLOUDFLARE_ZONE_ID; do
        [ -n "${!var:-}" ] || missing+=("$var")
    done
    if [ ${#missing[@]} -gt 0 ]; then
        log_error "Missing in $PLAYIT_CONFIG: ${missing[*]}"
        exit 2
    fi
}

# Print "<port> <target>" from playit's own SRV record, looked up over
# DNS-over-HTTPS (the Pi has no dig). Fails unless there is exactly one
# answer, its target is PLAYIT_HOST, and its port is a real port number.
playit_srv() {
    local response
    response=$(curl -fsS -m 10 -H "accept: application/dns-json" \
        "${DOH_URL}?name=_minecraft._tcp.${PLAYIT_HOST}&type=SRV") || return 1
    PLAYIT_HOST="$PLAYIT_HOST" python3 -c '
import json, os, sys
host = os.environ["PLAYIT_HOST"].rstrip(".").lower()
answers = [a for a in json.load(sys.stdin).get("Answer", []) if a.get("type") == 33]
if len(answers) != 1:
    sys.exit("expected one SRV answer, got %d" % len(answers))
priority, weight, port, target = answers[0]["data"].split()
target = target.rstrip(".").lower()
if target != host:
    sys.exit("SRV target %s is not %s" % (target, host))
if not port.isdigit() or not 0 < int(port) < 65536:
    sys.exit("SRV port %r is not a port number" % port)
print(port, target)
' <<< "$response"
}

# Print "<id> <priority> <weight> <port> <target>" for the Cloudflare record.
cloudflare_srv() {
    local response
    response=$(curl -fsS -m 10 \
        -H "Authorization: Bearer ${CLOUDFLARE_API_TOKEN}" \
        "${CF_API}/zones/${CLOUDFLARE_ZONE_ID}/dns_records?type=SRV&name=${GAME_SRV_NAME}") || return 1
    python3 -c '
import json, sys
d = json.load(sys.stdin)
if not d.get("success"):
    sys.exit("Cloudflare API error: %s" % d.get("errors"))
records = d.get("result", [])
if len(records) != 1:
    sys.exit("expected one SRV record, got %d" % len(records))
r = records[0]
data = r["data"]
print(r["id"], data["priority"], data["weight"], data["port"], data["target"].rstrip(".").lower())
' <<< "$response"
}

update_cloudflare() {
    local id="$1" priority="$2" weight="$3" port="$4" target="$5" response
    response=$(curl -fsS -m 10 -X PATCH \
        -H "Authorization: Bearer ${CLOUDFLARE_API_TOKEN}" \
        -H "Content-Type: application/json" \
        --data "{\"data\":{\"priority\":${priority},\"weight\":${weight},\"port\":${port},\"target\":\"${target}\"}}" \
        "${CF_API}/zones/${CLOUDFLARE_ZONE_ID}/dns_records/${id}") || return 1
    grep -q '"success": *true' <<< "$response"
}

main() {
    local mode="${1:-}"
    case "$mode" in
        check|sync) ;;
        -h|--help|help) usage; exit 0 ;;
        *) usage >&2; exit 2 ;;
    esac

    load_config

    local want have
    if ! want=$(playit_srv); then
        log_error "Could not read playit's SRV record for ${PLAYIT_HOST}; changing nothing"
        exit 1
    fi
    if ! have=$(cloudflare_srv); then
        log_error "Could not read the Cloudflare SRV record ${GAME_SRV_NAME}; changing nothing"
        exit 1
    fi

    local want_port want_target id priority weight have_port have_target
    read -r want_port want_target <<< "$want"
    read -r id priority weight have_port have_target <<< "$have"

    if [ "$want_port" = "$have_port" ] && [ "$want_target" = "$have_target" ]; then
        log_info "In sync: ${GAME_SRV_NAME} -> ${have_target}:${have_port}"
        exit 0
    fi

    log_warn "Out of sync: ${GAME_SRV_NAME} -> ${have_target}:${have_port}, playit says ${want_target}:${want_port}"
    [ "$mode" = sync ] || exit 1

    if update_cloudflare "$id" "$priority" "$weight" "$want_port" "$want_target"; then
        log_success "Updated ${GAME_SRV_NAME} -> ${want_target}:${want_port}"
    else
        log_error "Cloudflare update failed"
        exit 1
    fi
}

main "$@"
