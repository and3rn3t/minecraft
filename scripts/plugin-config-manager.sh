#!/bin/bash
# Plugin Configuration Manager
# Manages plugin configuration files, validation, and templates

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

PLUGIN_CONFIG_DIR="${PROJECT_DIR}/data/plugins"
PLUGIN_TEMPLATE_DIR="${PROJECT_DIR}/config/plugin-templates"

# Ensure directories exist
mkdir -p "$PLUGIN_CONFIG_DIR" "$PLUGIN_TEMPLATE_DIR"

# Function to validate YAML file
validate_yaml() {
    local file="$1"

    if [ ! -f "$file" ]; then
        return 1
    fi

    # Basic YAML validation (check for common syntax errors)
    # This is a simple check - full validation would require a YAML parser
    local errors=0

    # Check for unmatched brackets
    local open_braces=$(grep -o '{' "$file" | wc -l)
    local close_braces=$(grep -o '}' "$file" | wc -l)

    if [ "$open_braces" -ne "$close_braces" ]; then
        echo "  Unmatched braces"
        errors=$((errors + 1))
    fi

    # Check for basic syntax (key: value format)
    if ! grep -qE '^[a-zA-Z_][a-zA-Z0-9_]*:' "$file" 2>/dev/null; then
        echo "  No valid YAML keys found"
        errors=$((errors + 1))
    fi

    return $errors
}

# Function to validate plugin config
validate_plugin_config() {
    local plugin_name="$1"
    local config_file="$2"

    if [ -z "$config_file" ]; then
        # Try to find config file
        if [ -d "${PLUGIN_CONFIG_DIR}/${plugin_name}" ]; then
            config_file="${PLUGIN_CONFIG_DIR}/${plugin_name}/config.yml"
        else
            echo -e "${YELLOW}No configuration found for plugin: $plugin_name${NC}"
            return 1
        fi
    fi

    if [ ! -f "$config_file" ]; then
        echo -e "${RED}Configuration file not found: $config_file${NC}"
        return 1
    fi

    echo -e "${BLUE}Validating configuration: $config_file${NC}"

    local errors=0

    # Check file extension
    if [[ "$config_file" =~ \.(yml|yaml)$ ]]; then
        local validation_errors=$(validate_yaml "$config_file")
        if [ $? -ne 0 ]; then
            echo -e "${RED}YAML validation errors:${NC}"
            echo "$validation_errors"
            errors=$((errors + 1))
        fi
    fi

    # Check file is readable
    if [ ! -r "$config_file" ]; then
        echo -e "${RED}Configuration file is not readable${NC}"
        errors=$((errors + 1))
    fi

    # Check file is not empty
    if [ ! -s "$config_file" ]; then
        echo -e "${YELLOW}Warning: Configuration file is empty${NC}"
        errors=$((errors + 1))
    fi

    if [ $errors -eq 0 ]; then
        echo -e "${GREEN}Configuration is valid${NC}"
        return 0
    else
        echo -e "${RED}Configuration has $errors error(s)${NC}"
        return 1
    fi
}

# Function to list plugin configs
list_plugin_configs() {
    echo -e "${BLUE}Plugin Configurations:${NC}"
    echo ""

    if [ ! -d "$PLUGIN_CONFIG_DIR" ] || [ -z "$(ls -A "$PLUGIN_CONFIG_DIR" 2>/dev/null)" ]; then
        echo -e "  ${YELLOW}No plugin configurations found${NC}"
        return 0
    fi

    local count=0
    for plugin_dir in "$PLUGIN_CONFIG_DIR"/*; do
        if [ -d "$plugin_dir" ]; then
            count=$((count + 1))
            local plugin_name=$(basename "$plugin_dir")
            local config_count=$(find "$plugin_dir" -name "*.yml" -o -name "*.yaml" -o -name "*.properties" -o -name "*.conf" | wc -l)
            echo -e "  ${GREEN}✓${NC} $plugin_name ($config_count config file(s))"
        fi
    done

    echo ""
    echo -e "${GREEN}Total: $count plugin(s) with configurations${NC}"
}

# Function to backup plugin config
backup_plugin_config() {
    local plugin_name="$1"
    local backup_dir="${PROJECT_DIR}/backups/plugins/configs"

    if [ -z "$plugin_name" ]; then
        echo -e "${RED}Error: Plugin name not specified${NC}"
        return 1
    fi

    local config_path="${PLUGIN_CONFIG_DIR}/${plugin_name}"

    if [ ! -d "$config_path" ]; then
        echo -e "${YELLOW}No configuration found for plugin: $plugin_name${NC}"
        return 1
    fi

    mkdir -p "$backup_dir"
    local backup_file="${backup_dir}/${plugin_name}.$(date +%Y%m%d_%H%M%S).tar.gz"

    echo -e "${BLUE}Backing up configuration for: $plugin_name${NC}"
    tar -czf "$backup_file" -C "$PLUGIN_CONFIG_DIR" "$plugin_name"

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}Configuration backed up: $backup_file${NC}"
    else
        echo -e "${RED}Backup failed${NC}"
        return 1
    fi
}

# Function to restore plugin config
restore_plugin_config() {
    local plugin_name="$1"
    local backup_file="$2"

    if [ -z "$plugin_name" ] || [ -z "$backup_file" ]; then
        echo -e "${RED}Error: Plugin name and backup file required${NC}"
        return 1
    fi

    if [ ! -f "$backup_file" ]; then
        echo -e "${RED}Error: Backup file not found: $backup_file${NC}"
        return 1
    fi

    # Backup current config first
    if [ -d "${PLUGIN_CONFIG_DIR}/${plugin_name}" ]; then
        backup_plugin_config "$plugin_name"
    fi

    echo -e "${BLUE}Restoring configuration for: $plugin_name${NC}"

    # Extract backup
    tar -xzf "$backup_file" -C "$PLUGIN_CONFIG_DIR"

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}Configuration restored${NC}"
    else
        echo -e "${RED}Restore failed${NC}"
        return 1
    fi
}

# Function to create config template
create_config_template() {
    local plugin_name="$1"
    local template_file="${PLUGIN_TEMPLATE_DIR}/${plugin_name}.template.yml"

    if [ -z "$plugin_name" ]; then
        echo -e "${RED}Error: Plugin name not specified${NC}"
        return 1
    fi

    # Check if template already exists
    if [ -f "$template_file" ]; then
        echo -e "${YELLOW}Template already exists: $template_file${NC}"
        read -p "Overwrite? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            return 0
        fi
    fi

    # Try to copy from existing config
    local config_file="${PLUGIN_CONFIG_DIR}/${plugin_name}/config.yml"
    if [ -f "$config_file" ]; then
        cp "$config_file" "$template_file"
        echo -e "${GREEN}Template created from existing config: $template_file${NC}"
    else
        # Create a basic template
        cat > "$template_file" <<EOF
# Configuration template for $plugin_name
# Copy this file to data/plugins/$plugin_name/config.yml and customize

# Example configuration
# settings:
#   enabled: true
#   option1: value1
#   option2: value2
EOF
        echo -e "${GREEN}Basic template created: $template_file${NC}"
    fi
}

# Function to apply config template
apply_config_template() {
    local plugin_name="$1"
    local template_file="${PLUGIN_TEMPLATE_DIR}/${plugin_name}.template.yml"

    if [ -z "$plugin_name" ]; then
        echo -e "${RED}Error: Plugin name not specified${NC}"
        return 1
    fi

    if [ ! -f "$template_file" ]; then
        echo -e "${RED}Error: Template not found: $template_file${NC}"
        return 1
    fi

    local config_dir="${PLUGIN_CONFIG_DIR}/${plugin_name}"
    mkdir -p "$config_dir"

    local config_file="${config_dir}/config.yml"

    # Backup existing config if it exists
    if [ -f "$config_file" ]; then
        backup_plugin_config "$plugin_name"
    fi

    cp "$template_file" "$config_file"
    echo -e "${GREEN}Template applied: $config_file${NC}"
    echo -e "${YELLOW}Note: Customize the configuration file as needed${NC}"
}

# Function to display usage
usage() {
    echo -e "${BLUE}Plugin Configuration Manager${NC}"
    echo ""
    echo "Usage: $0 {list|validate|backup|restore|create-template|apply-template} [options]"
    echo ""
    echo "Commands:"
    echo "  list                    - List all plugin configurations"
    echo "  validate <plugin> [file] - Validate plugin configuration"
    echo "  backup <plugin>         - Backup plugin configuration"
    echo "  restore <plugin> <file> - Restore plugin configuration from backup"
    echo "  create-template <plugin> - Create configuration template"
    echo "  apply-template <plugin>  - Apply configuration template"
    echo ""
    exit 1
}

# Main function
main() {
    case "${1}" in
        list)
            list_plugin_configs
            ;;
        validate)
            if [ -z "$2" ]; then
                echo -e "${RED}Error: Plugin name not specified${NC}"
                usage
            fi
            validate_plugin_config "$2" "$3"
            ;;
        backup)
            if [ -z "$2" ]; then
                echo -e "${RED}Error: Plugin name not specified${NC}"
                usage
            fi
            backup_plugin_config "$2"
            ;;
        restore)
            if [ -z "$2" ] || [ -z "$3" ]; then
                echo -e "${RED}Error: Plugin name and backup file required${NC}"
                usage
            fi
            restore_plugin_config "$2" "$3"
            ;;
        create-template)
            if [ -z "$2" ]; then
                echo -e "${RED}Error: Plugin name not specified${NC}"
                usage
            fi
            create_config_template "$2"
            ;;
        apply-template)
            if [ -z "$2" ]; then
                echo -e "${RED}Error: Plugin name not specified${NC}"
                usage
            fi
            apply_config_template "$2"
            ;;
        *)
            usage
            ;;
    esac
}

# Run main function
main "$@"

