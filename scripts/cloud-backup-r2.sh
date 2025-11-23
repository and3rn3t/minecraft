#!/bin/bash
# Cloudflare R2 Backup Script
# Uploads and restores backups from Cloudflare R2 (S3-compatible)

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
CONFIG_FILE="${PROJECT_DIR}/config/cloud-backup-r2.conf"

# Load configuration
if [ -f "$CONFIG_FILE" ]; then
    source "$CONFIG_FILE"
else
    echo -e "${YELLOW}Config file not found: $CONFIG_FILE${NC}"
    echo "Creating example config..."
    mkdir -p "$(dirname "$CONFIG_FILE")"
    cat > "$CONFIG_FILE" << 'EOF'
# Cloudflare R2 Backup Configuration
# Copy this to config/cloud-backup-r2.conf and fill in your credentials

# R2 Account ID (found in Cloudflare dashboard)
R2_ACCOUNT_ID=""

# R2 Access Key ID
R2_ACCESS_KEY_ID=""

# R2 Secret Access Key
R2_SECRET_ACCESS_KEY=""

# R2 Bucket Name
R2_BUCKET_NAME=""

# R2 Endpoint (usually: https://<account-id>.r2.cloudflarestorage.com)
R2_ENDPOINT=""

# Backup prefix in bucket (optional)
R2_PREFIX="minecraft-backups"
EOF
    echo -e "${GREEN}Example config created: $CONFIG_FILE${NC}"
    echo "Please edit the config file with your R2 credentials"
    exit 1
fi

# Check required configuration
if [ -z "$R2_ACCOUNT_ID" ] || [ -z "$R2_ACCESS_KEY_ID" ] || [ -z "$R2_SECRET_ACCESS_KEY" ] || [ -z "$R2_BUCKET_NAME" ] || [ -z "$R2_ENDPOINT" ]; then
    echo -e "${RED}Error: R2 configuration incomplete${NC}"
    echo "Please configure $CONFIG_FILE with your R2 credentials"
    exit 1
fi

# Check for AWS CLI (used for S3-compatible operations)
if ! command -v aws >/dev/null 2>&1; then
    echo -e "${YELLOW}AWS CLI not found. Installing...${NC}"
    echo "Please install AWS CLI: https://aws.amazon.com/cli/"
    echo "Or use: pip install awscli"
    exit 1
fi

# Configure AWS CLI for R2
export AWS_ACCESS_KEY_ID="$R2_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$R2_SECRET_ACCESS_KEY"
export AWS_DEFAULT_REGION="auto"

# Function to upload backup
upload_backup() {
    local backup_file="$1"

    if [ -z "$backup_file" ]; then
        echo -e "${RED}Error: Backup file not specified${NC}"
        exit 1
    fi

    if [ ! -f "$backup_file" ]; then
        echo -e "${RED}Error: Backup file not found: $backup_file${NC}"
        exit 1
    fi

    local backup_name=$(basename "$backup_file")
    local r2_key="${R2_PREFIX}/${backup_name}"

    echo -e "${BLUE}Uploading backup to R2...${NC}"
    echo -e "  File: $backup_file"
    echo -e "  Key: $r2_key"
    echo -e "  Bucket: $R2_BUCKET_NAME"
    echo ""

    # Upload using AWS CLI with R2 endpoint
    if aws s3 cp "$backup_file" "s3://${R2_BUCKET_NAME}/${r2_key}" \
        --endpoint-url="$R2_ENDPOINT" \
        --no-verify-ssl; then
        echo -e "${GREEN}✓ Backup uploaded successfully!${NC}"
        echo ""
        echo "Backup URL: ${R2_ENDPOINT}/${R2_BUCKET_NAME}/${r2_key}"
        return 0
    else
        echo -e "${RED}✗ Upload failed${NC}"
        return 1
    fi
}

# Function to list backups
list_backups() {
    echo -e "${BLUE}Listing backups in R2...${NC}"
    echo ""

    aws s3 ls "s3://${R2_BUCKET_NAME}/${R2_PREFIX}/" \
        --endpoint-url="$R2_ENDPOINT" \
        --no-verify-ssl \
        --human-readable \
        --summarize | while IFS= read -r line; do
        echo "  $line"
    done
}

# Function to download backup
download_backup() {
    local backup_name="$1"
    local output_dir="${2:-${PROJECT_DIR}/backups}"

    if [ -z "$backup_name" ]; then
        echo -e "${RED}Error: Backup name not specified${NC}"
        echo "Usage: $0 download <backup-name> [output-dir]"
        exit 1
    fi

    local r2_key="${R2_PREFIX}/${backup_name}"
    local output_file="${output_dir}/${backup_name}"

    mkdir -p "$output_dir"

    echo -e "${BLUE}Downloading backup from R2...${NC}"
    echo -e "  Key: $r2_key"
    echo -e "  Output: $output_file"
    echo ""

    if aws s3 cp "s3://${R2_BUCKET_NAME}/${r2_key}" "$output_file" \
        --endpoint-url="$R2_ENDPOINT" \
        --no-verify-ssl; then
        echo -e "${GREEN}✓ Backup downloaded successfully!${NC}"
        echo "Location: $output_file"
        return 0
    else
        echo -e "${RED}✗ Download failed${NC}"
        return 1
    fi
}

# Function to delete backup
delete_backup() {
    local backup_name="$1"

    if [ -z "$backup_name" ]; then
        echo -e "${RED}Error: Backup name not specified${NC}"
        echo "Usage: $0 delete <backup-name>"
        exit 1
    fi

    local r2_key="${R2_PREFIX}/${backup_name}"

    echo -e "${YELLOW}Warning: This will permanently delete the backup from R2${NC}"
    echo -e "  Key: $r2_key"
    read -p "Are you sure? (yes/no): " confirm

    if [ "$confirm" != "yes" ]; then
        echo "Cancelled"
        return 0
    fi

    if aws s3 rm "s3://${R2_BUCKET_NAME}/${r2_key}" \
        --endpoint-url="$R2_ENDPOINT" \
        --no-verify-ssl; then
        echo -e "${GREEN}✓ Backup deleted successfully!${NC}"
        return 0
    else
        echo -e "${RED}✗ Delete failed${NC}"
        return 1
    fi
}

# Function to sync local backups to R2
sync_backups() {
    local backup_dir="${PROJECT_DIR}/backups"

    if [ ! -d "$backup_dir" ]; then
        echo -e "${RED}Error: Backup directory not found: $backup_dir${NC}"
        exit 1
    fi

    echo -e "${BLUE}Syncing local backups to R2...${NC}"
    echo ""

    local count=0
    for backup_file in "$backup_dir"/*.tar.gz; do
        if [ -f "$backup_file" ]; then
            if upload_backup "$backup_file"; then
                count=$((count + 1))
            fi
        fi
    done

    echo ""
    echo -e "${GREEN}✓ Synced $count backup(s) to R2${NC}"
}

# Function to test R2 connection
test_connection() {
    echo -e "${BLUE}Testing R2 connection...${NC}"
    echo ""

    # Test bucket access
    if aws s3 ls "s3://${R2_BUCKET_NAME}/" \
        --endpoint-url="$R2_ENDPOINT" \
        --no-verify-ssl >/dev/null 2>&1; then
        echo -e "${GREEN}✓ R2 connection successful!${NC}"
        echo ""
        echo "Configuration:"
        echo "  Account ID: $R2_ACCOUNT_ID"
        echo "  Bucket: $R2_BUCKET_NAME"
        echo "  Endpoint: $R2_ENDPOINT"
        echo "  Prefix: $R2_PREFIX"
        return 0
    else
        echo -e "${RED}✗ R2 connection failed${NC}"
        echo "Please check your credentials and configuration"
        return 1
    fi
}

# Main function
main() {
    local command="${1:-help}"

    case "$command" in
        upload)
            upload_backup "$2"
            ;;
        download)
            download_backup "$2" "$3"
            ;;
        list)
            list_backups
            ;;
        delete)
            delete_backup "$2"
            ;;
        sync)
            sync_backups
            ;;
        test)
            test_connection
            ;;
        help|*)
            echo -e "${BLUE}Cloudflare R2 Backup Manager${NC}"
            echo ""
            echo "Usage: $0 {upload|download|list|delete|sync|test|help} [options]"
            echo ""
            echo "Commands:"
            echo "  upload <file>           - Upload backup file to R2"
            echo "  download <name> [dir]   - Download backup from R2"
            echo "  list                   - List backups in R2"
            echo "  delete <name>          - Delete backup from R2"
            echo "  sync                   - Sync all local backups to R2"
            echo "  test                   - Test R2 connection"
            echo "  help                   - Show this help message"
            echo ""
            echo "Configuration:"
            echo "  Config file: $CONFIG_FILE"
            echo ""
            echo "Examples:"
            echo "  $0 upload backups/minecraft_backup_20250127.tar.gz"
            echo "  $0 download minecraft_backup_20250127.tar.gz"
            echo "  $0 list"
            echo "  $0 sync"
            echo ""
            exit 1
            ;;
    esac
}

# Run main function
main "$@"

