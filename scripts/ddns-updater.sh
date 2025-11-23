#!/bin/bash
set -e

# Dynamic DNS Updater Script
# Supports DuckDNS, No-IP, and Cloudflare DNS

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
CONFIG_DIR="$PROJECT_ROOT/config"
DDNS_CONFIG="$CONFIG_DIR/ddns.conf"
LOG_FILE="$PROJECT_ROOT/logs/ddns-updater.log"

# Create logs directory if it doesn't exist
mkdir -p "$(dirname "$LOG_FILE")"

# Logging function
log() {
    local level="$1"
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] [$level] $message" >> "$LOG_FILE"

    case "$level" in
        ERROR)
            echo -e "${RED}[ERROR]${NC} $message" >&2
            ;;
        WARN)
            echo -e "${YELLOW}[WARN]${NC} $message"
            ;;
        INFO)
            echo -e "${BLUE}[INFO]${NC} $message"
            ;;
        SUCCESS)
            echo -e "${GREEN}[SUCCESS]${NC} $message"
            ;;
    esac
}

# Load configuration
load_config() {
    if [ ! -f "$DDNS_CONFIG" ]; then
        log ERROR "Configuration file not found: $DDNS_CONFIG"
        log INFO "Creating default configuration file..."
        create_default_config
    fi

    # Source the config file
    source "$DDNS_CONFIG"

    # Validate required settings
    if [ -z "$DDNS_PROVIDER" ]; then
        log ERROR "DDNS_PROVIDER not set in $DDNS_CONFIG"
        exit 1
    fi
}

# Create default configuration file
create_default_config() {
    cat > "$DDNS_CONFIG" << 'EOF'
# Dynamic DNS Configuration
# Provider options: duckdns, noip, cloudflare

# Provider selection
DDNS_PROVIDER=duckdns

# Update interval in minutes (default: 5)
DDNS_UPDATE_INTERVAL=5

# DuckDNS Settings
DUCKDNS_TOKEN=
DUCKDNS_DOMAIN=

# No-IP Settings
NOIP_USERNAME=
NOIP_PASSWORD=
NOIP_DOMAIN=
NOIP_HOSTNAME=

# Cloudflare Settings
CLOUDFLARE_API_TOKEN=
CLOUDFLARE_ZONE_ID=
CLOUDFLARE_DOMAIN=
CLOUDFLARE_RECORD_NAME=

# Advanced Settings
DDNS_ENABLED=false
DDNS_IP_CHECK_URL=https://api.ipify.org
DDNS_VERIFY_SSL=true
EOF
    chmod 600 "$DDNS_CONFIG"
    log INFO "Default configuration created at $DDNS_CONFIG"
    log WARN "Please edit $DDNS_CONFIG and configure your DNS provider settings"
}

# Get current public IP
get_public_ip() {
    local ip_check_url="${DDNS_IP_CHECK_URL:-https://api.ipify.org}"

    if [ "$DDNS_VERIFY_SSL" = "false" ]; then
        curl_opts="-k"
    else
        curl_opts=""
    fi

    local ip=$(curl -s $curl_opts "$ip_check_url" 2>/dev/null || echo "")

    if [ -z "$ip" ]; then
        # Fallback to alternative service
        ip=$(curl -s $curl_opts "https://icanhazip.com" 2>/dev/null || echo "")
    fi

    if [ -z "$ip" ]; then
        log ERROR "Failed to get public IP address"
        return 1
    fi

    # Validate IP format
    if [[ ! $ip =~ ^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$ ]]; then
        log ERROR "Invalid IP address format: $ip"
        return 1
    fi

    echo "$ip"
}

# Update DuckDNS
update_duckdns() {
    if [ -z "$DUCKDNS_TOKEN" ] || [ -z "$DUCKDNS_DOMAIN" ]; then
        log ERROR "DuckDNS configuration incomplete. Set DUCKDNS_TOKEN and DUCKDNS_DOMAIN in $DDNS_CONFIG"
        return 1
    fi

    local current_ip=$(get_public_ip)
    if [ $? -ne 0 ]; then
        return 1
    fi

    log INFO "Updating DuckDNS for domain: $DUCKDNS_DOMAIN"
    log INFO "Current public IP: $current_ip"

    local url="https://www.duckdns.org/update?domains=$DUCKDNS_DOMAIN&token=$DUCKDNS_TOKEN&ip=$current_ip"

    local response=$(curl -s "$url" 2>/dev/null)

    if [ "$response" = "OK" ]; then
        log SUCCESS "DuckDNS updated successfully: $DUCKDNS_DOMAIN -> $current_ip"
        return 0
    else
        log ERROR "DuckDNS update failed: $response"
        return 1
    fi
}

# Update No-IP
update_noip() {
    if [ -z "$NOIP_USERNAME" ] || [ -z "$NOIP_PASSWORD" ] || [ -z "$NOIP_DOMAIN" ]; then
        log ERROR "No-IP configuration incomplete. Set NOIP_USERNAME, NOIP_PASSWORD, and NOIP_DOMAIN in $DDNS_CONFIG"
        return 1
    fi

    local current_ip=$(get_public_ip)
    if [ $? -ne 0 ]; then
        return 1
    fi

    local hostname="${NOIP_HOSTNAME:-$NOIP_DOMAIN}"

    log INFO "Updating No-IP for domain: $hostname"
    log INFO "Current public IP: $current_ip"

    local url="https://$NOIP_USERNAME:$NOIP_PASSWORD@dynupdate.no-ip.com/nic/update?hostname=$hostname&myip=$current_ip"

    local response=$(curl -s "$url" 2>/dev/null)

    if [[ "$response" =~ ^(good|nochg) ]]; then
        log SUCCESS "No-IP updated successfully: $hostname -> $current_ip"
        return 0
    else
        log ERROR "No-IP update failed: $response"
        return 1
    fi
}

# Update Cloudflare DNS
update_cloudflare() {
    if [ -z "$CLOUDFLARE_API_TOKEN" ] || [ -z "$CLOUDFLARE_ZONE_ID" ] || [ -z "$CLOUDFLARE_DOMAIN" ]; then
        log ERROR "Cloudflare configuration incomplete. Set CLOUDFLARE_API_TOKEN, CLOUDFLARE_ZONE_ID, and CLOUDFLARE_DOMAIN in $DDNS_CONFIG"
        return 1
    fi

    local current_ip=$(get_public_ip)
    if [ $? -ne 0 ]; then
        return 1
    fi

    local record_name="${CLOUDFLARE_RECORD_NAME:-$CLOUDFLARE_DOMAIN}"

    log INFO "Updating Cloudflare DNS for: $record_name"
    log INFO "Current public IP: $current_ip"

    # Get existing record ID
    local record_response=$(curl -s -X GET \
        "https://api.cloudflare.com/client/v4/zones/$CLOUDFLARE_ZONE_ID/dns_records?type=A&name=$record_name" \
        -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" \
        -H "Content-Type: application/json" 2>/dev/null)

    local record_id=$(echo "$record_response" | grep -o '"id":"[^"]*' | head -1 | cut -d'"' -f4)

    if [ -z "$record_id" ]; then
        log ERROR "DNS record not found: $record_name"
        return 1
    fi

    # Update the record
    local update_response=$(curl -s -X PUT \
        "https://api.cloudflare.com/client/v4/zones/$CLOUDFLARE_ZONE_ID/dns_records/$record_id" \
        -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" \
        -H "Content-Type: application/json" \
        --data "{\"type\":\"A\",\"name\":\"$record_name\",\"content\":\"$current_ip\",\"ttl\":300}" 2>/dev/null)

    local success=$(echo "$update_response" | grep -o '"success":true' || echo "")

    if [ -n "$success" ]; then
        log SUCCESS "Cloudflare DNS updated successfully: $record_name -> $current_ip"
        return 0
    else
        log ERROR "Cloudflare DNS update failed"
        log ERROR "Response: $update_response"
        return 1
    fi
}

# Main update function
update_dns() {
    load_config

    if [ "$DDNS_ENABLED" != "true" ]; then
        log WARN "DDNS is disabled. Set DDNS_ENABLED=true in $DDNS_CONFIG to enable"
        return 0
    fi

    case "$DDNS_PROVIDER" in
        duckdns)
            update_duckdns
            ;;
        noip)
            update_noip
            ;;
        cloudflare)
            update_cloudflare
            ;;
        *)
            log ERROR "Unknown DDNS provider: $DDNS_PROVIDER"
            log ERROR "Supported providers: duckdns, noip, cloudflare"
            return 1
            ;;
    esac
}

# Run as daemon (continuous updates)
run_daemon() {
    load_config

    if [ "$DDNS_ENABLED" != "true" ]; then
        log WARN "DDNS is disabled. Set DDNS_ENABLED=true in $DDNS_CONFIG to enable"
        exit 0
    fi

    local interval="${DDNS_UPDATE_INTERVAL:-5}"
    log INFO "Starting DDNS updater daemon (update interval: ${interval} minutes)"

    while true; do
        update_dns
        sleep $((interval * 60))
    done
}

# Usage function
usage() {
    cat << EOF
Usage: $0 [COMMAND]

Dynamic DNS Updater for Minecraft Server Management

Commands:
    update          Update DNS record once
    daemon         Run as daemon (continuous updates)
    config         Create default configuration file
    status         Show current configuration and status
    help           Show this help message

Examples:
    $0 update              # Update DNS once
    $0 daemon             # Run continuous updates
    $0 config             # Create default config file
    $0 status             # Show current status

Configuration:
    Edit $DDNS_CONFIG to configure your DNS provider

Supported Providers:
    - DuckDNS (duckdns.org)
    - No-IP (noip.com)
    - Cloudflare (cloudflare.com)

EOF
}

# Status function
show_status() {
    if [ ! -f "$DDNS_CONFIG" ]; then
        log WARN "Configuration file not found: $DDNS_CONFIG"
        log INFO "Run '$0 config' to create default configuration"
        return 1
    fi

    load_config

    echo -e "${BLUE}=== DDNS Configuration Status ===${NC}"
    echo "Provider: $DDNS_PROVIDER"
    echo "Enabled: $DDNS_ENABLED"
    echo "Update Interval: ${DDNS_UPDATE_INTERVAL:-5} minutes"
    echo ""

    case "$DDNS_PROVIDER" in
        duckdns)
            if [ -n "$DUCKDNS_DOMAIN" ]; then
                echo "Domain: $DUCKDNS_DOMAIN"
            else
                echo -e "${RED}Domain: Not configured${NC}"
            fi
            if [ -n "$DUCKDNS_TOKEN" ]; then
                echo "Token: ${DUCKDNS_TOKEN:0:4}...${DUCKDNS_TOKEN: -4} (hidden)"
            else
                echo -e "${RED}Token: Not configured${NC}"
            fi
            ;;
        noip)
            if [ -n "$NOIP_DOMAIN" ]; then
                echo "Domain: $NOIP_DOMAIN"
            else
                echo -e "${RED}Domain: Not configured${NC}"
            fi
            if [ -n "$NOIP_USERNAME" ]; then
                echo "Username: $NOIP_USERNAME"
            else
                echo -e "${RED}Username: Not configured${NC}"
            fi
            ;;
        cloudflare)
            if [ -n "$CLOUDFLARE_DOMAIN" ]; then
                echo "Domain: $CLOUDFLARE_DOMAIN"
            else
                echo -e "${RED}Domain: Not configured${NC}"
            fi
            if [ -n "$CLOUDFLARE_ZONE_ID" ]; then
                echo "Zone ID: $CLOUDFLARE_ZONE_ID"
            else
                echo -e "${RED}Zone ID: Not configured${NC}"
            fi
            ;;
    esac

    echo ""
    echo "Current Public IP: $(get_public_ip 2>/dev/null || echo 'Unable to determine')"
}

# Main execution
main() {
    case "${1:-help}" in
        update)
            update_dns
            ;;
        daemon)
            run_daemon
            ;;
        config)
            create_default_config
            ;;
        status)
            show_status
            ;;
        help|--help|-h)
            usage
            ;;
        *)
            log ERROR "Unknown command: $1"
            usage
            exit 1
            ;;
    esac
}

# Run main function
main "$@"

