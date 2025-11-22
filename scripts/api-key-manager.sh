#!/bin/bash
# API Key Manager
# Manages API keys for the REST API

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
API_KEYS_FILE="${PROJECT_DIR}/config/api-keys.json"

# Ensure config directory exists
mkdir -p "$(dirname "$API_KEYS_FILE")"

# Function to generate API key
generate_api_key() {
    # Generate 32-character random key
    if [ -c /dev/urandom ]; then
        tr -dc 'A-Za-z0-9' < /dev/urandom | head -c 32
        echo
    else
        openssl rand -hex 16
    fi
}

# Function to load API keys
load_keys() {
    if [ -f "$API_KEYS_FILE" ]; then
        cat "$API_KEYS_FILE"
    else
        echo "{}"
    fi
}

# Function to save API keys
save_keys() {
    local keys_json="$1"
    echo "$keys_json" > "$API_KEYS_FILE"
    chmod 600 "$API_KEYS_FILE"
}

# Function to create API key
create_key() {
    local name="$1"
    local description="${2:-}"

    if [ -z "$name" ]; then
        echo -e "${RED}Error: Key name required${NC}"
        echo -e "${YELLOW}Usage: $0 create <name> [description]${NC}"
        return 1
    fi

    local api_key=$(generate_api_key)
    local keys_json=$(load_keys)

    # Create new key entry
    local new_key=$(cat <<EOF
{
    "name": "$name",
    "description": "$description",
    "enabled": true,
    "created": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF
)

    # Add to keys JSON (using Python for JSON manipulation)
    local updated_json=$(python3 <<PYTHON
import json
import sys

keys = json.loads('''$keys_json''')
keys['$api_key'] = json.loads('''$new_key''')
print(json.dumps(keys, indent=2))
PYTHON
)

    save_keys "$updated_json"

    echo -e "${GREEN}API key created${NC}"
    echo -e "${BLUE}Name: $name${NC}"
    echo -e "${BLUE}Key: $api_key${NC}"
    echo ""
    echo -e "${YELLOW}IMPORTANT: Save this key securely!${NC}"
    echo -e "${YELLOW}It will not be shown again.${NC}"
}

# Function to list API keys
list_keys() {
    local keys_json=$(load_keys)

    if [ "$keys_json" = "{}" ]; then
        echo -e "${YELLOW}No API keys found${NC}"
        return 0
    fi

    echo -e "${BLUE}API Keys:${NC}"
    echo ""

    python3 <<PYTHON
import json
import sys

keys = json.loads('''$keys_json''')
for key, info in keys.items():
    status = "✓" if info.get('enabled', True) else "✗"
    name = info.get('name', 'Unknown')
    desc = info.get('description', '')
    created = info.get('created', 'Unknown')
    key_preview = key[:8] + "..." + key[-4:]
    print(f"  {status} {name} ({key_preview})")
    if desc:
        print(f"    Description: {desc}")
    print(f"    Created: {created}")
    print("")
PYTHON
}

# Function to disable API key
disable_key() {
    local key_preview="$1"

    if [ -z "$key_preview" ]; then
        echo -e "${RED}Error: Key identifier required${NC}"
        return 1
    fi

    local keys_json=$(load_keys)

    # Find and disable key
    local updated_json=$(python3 <<PYTHON
import json
import sys

keys = json.loads('''$keys_json''')
found = False
for key in keys:
    if key.startswith('$key_preview') or key.endswith('$key_preview'):
        keys[key]['enabled'] = False
        print(f"Disabled key: {keys[key].get('name', 'Unknown')}")
        found = True
        break

if not found:
    print("Key not found", file=sys.stderr)
    sys.exit(1)

print(json.dumps(keys, indent=2))
PYTHON
)

    if [ $? -eq 0 ]; then
        save_keys "$updated_json"
        echo -e "${GREEN}API key disabled${NC}"
    else
        echo -e "${RED}Error: Key not found${NC}"
        return 1
    fi
}

# Function to enable API key
enable_key() {
    local key_preview="$1"

    if [ -z "$key_preview" ]; then
        echo -e "${RED}Error: Key identifier required${NC}"
        return 1
    fi

    local keys_json=$(load_keys)

    # Find and enable key
    local updated_json=$(python3 <<PYTHON
import json
import sys

keys = json.loads('''$keys_json''')
found = False
for key in keys:
    if key.startswith('$key_preview') or key.endswith('$key_preview'):
        keys[key]['enabled'] = True
        print(f"Enabled key: {keys[key].get('name', 'Unknown')}")
        found = True
        break

if not found:
    print("Key not found", file=sys.stderr)
    sys.exit(1)

print(json.dumps(keys, indent=2))
PYTHON
)

    if [ $? -eq 0 ]; then
        save_keys "$updated_json"
        echo -e "${GREEN}API key enabled${NC}"
    else
        echo -e "${RED}Error: Key not found${NC}"
        return 1
    fi
}

# Function to delete API key
delete_key() {
    local key_preview="$1"

    if [ -z "$key_preview" ]; then
        echo -e "${RED}Error: Key identifier required${NC}"
        return 1
    fi

    local keys_json=$(load_keys)

    # Find and delete key
    local updated_json=$(python3 <<PYTHON
import json
import sys

keys = json.loads('''$keys_json''')
found = False
key_to_delete = None
for key in keys:
    if key.startswith('$key_preview') or key.endswith('$key_preview'):
        key_to_delete = key
        found = True
        break

if not found:
    print("Key not found", file=sys.stderr)
    sys.exit(1)

del keys[key_to_delete]
print(json.dumps(keys, indent=2))
PYTHON
)

    if [ $? -eq 0 ]; then
        save_keys "$updated_json"
        echo -e "${GREEN}API key deleted${NC}"
    else
        echo -e "${RED}Error: Key not found${NC}"
        return 1
    fi
}

# Function to display usage
usage() {
    echo -e "${BLUE}API Key Manager${NC}"
    echo ""
    echo "Usage: $0 {create|list|enable|disable|delete} [options]"
    echo ""
    echo "Commands:"
    echo "  create <name> [desc]  - Create a new API key"
    echo "  list                  - List all API keys"
    echo "  enable <key-preview>  - Enable an API key"
    echo "  disable <key-preview> - Disable an API key"
    echo "  delete <key-preview>  - Delete an API key"
    echo ""
    echo "Examples:"
    echo "  $0 create webhook \"Webhook integration\""
    echo "  $0 list"
    echo "  $0 disable abc12345"
    echo ""
    exit 1
}

# Main function
main() {
    case "${1:-}" in
        create)
            create_key "$2" "$3"
            ;;
        list)
            list_keys
            ;;
        enable)
            enable_key "$2"
            ;;
        disable)
            disable_key "$2"
            ;;
        delete)
            delete_key "$2"
            ;;
        *)
            usage
            ;;
    esac
}

# Run main function
main "$@"

