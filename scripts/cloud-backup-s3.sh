#!/bin/bash
# AWS S3 Backup Script
# Uploads and restores backups from AWS S3

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
CONFIG_FILE="${PROJECT_DIR}/config/cloud-backup-s3.conf"

# Load configuration
if [ -f "$CONFIG_FILE" ]; then
    source "$CONFIG_FILE"
else
    echo -e "${YELLOW}Config file not found: $CONFIG_FILE${NC}"
    echo "Creating example config..."
    mkdir -p "$(dirname "$CONFIG_FILE")"
    cat > "$CONFIG_FILE" << 'EOF'
# AWS S3 Backup Configuration
# Copy this to config/cloud-backup-s3.conf and fill in your credentials

# AWS Access Key ID
# Create in AWS IAM: IAM > Users > Security credentials > Create access key
AWS_ACCESS_KEY_ID=""

# AWS Secret Access Key
# Keep this secret! Never commit this file to git.
AWS_SECRET_ACCESS_KEY=""

# AWS Region
# e.g., us-east-1, eu-west-1, ap-southeast-1
AWS_REGION="us-east-1"

# S3 Bucket Name
# Must be globally unique
S3_BUCKET_NAME=""

# Backup prefix in bucket (optional)
# All backups will be stored under this prefix
S3_PREFIX="minecraft-backups"

# S3 Storage Class (optional)
# STANDARD, STANDARD_IA, ONEZONE_IA, GLACIER, DEEP_ARCHIVE
# Default: STANDARD (for frequent access)
S3_STORAGE_CLASS="STANDARD"

# Auto-upload after local backup (optional)
AUTO_UPLOAD="false"

# Auto-delete local after upload (optional, use with caution)
AUTO_DELETE_LOCAL="false"
EOF
    echo -e "${GREEN}Example config created: $CONFIG_FILE${NC}"
    echo "Please edit the config file with your AWS credentials"
    exit 1
fi

# Check required configuration
if [ -z "$AWS_ACCESS_KEY_ID" ] || [ -z "$AWS_SECRET_ACCESS_KEY" ] || [ -z "$S3_BUCKET_NAME" ] || [ -z "$AWS_REGION" ]; then
    echo -e "${RED}Error: S3 configuration incomplete${NC}"
    echo "Please configure $CONFIG_FILE with your AWS credentials"
    exit 1
fi

# Check for AWS CLI
if ! command -v aws >/dev/null 2>&1; then
    echo -e "${YELLOW}AWS CLI not found. Installing...${NC}"
    echo "Please install AWS CLI: https://aws.amazon.com/cli/"
    echo "Or use: pip install awscli"
    exit 1
fi

# Configure AWS CLI
export AWS_ACCESS_KEY_ID="$AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$AWS_SECRET_ACCESS_KEY"
export AWS_DEFAULT_REGION="${AWS_REGION:-us-east-1}"

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
    local s3_key="${S3_PREFIX}/${backup_name}"
    local storage_class="${S3_STORAGE_CLASS:-STANDARD}"

    echo -e "${BLUE}Uploading backup to S3...${NC}"
    echo -e "  File: $backup_file"
    echo -e "  Key: $s3_key"
    echo -e "  Bucket: $S3_BUCKET_NAME"
    echo -e "  Region: $AWS_REGION"
    echo -e "  Storage Class: $storage_class"
    echo ""

    # Upload using AWS CLI
    if aws s3 cp "$backup_file" "s3://${S3_BUCKET_NAME}/${s3_key}" \
        --storage-class "$storage_class" \
        --region "$AWS_REGION"; then
        echo -e "${GREEN}✓ Backup uploaded successfully!${NC}"
        echo ""
        echo "S3 URI: s3://${S3_BUCKET_NAME}/${s3_key}"
        return 0
    else
        echo -e "${RED}✗ Upload failed${NC}"
        return 1
    fi
}

# Function to list backups
list_backups() {
    echo -e "${BLUE}Listing backups in S3...${NC}"
    echo ""

    aws s3 ls "s3://${S3_BUCKET_NAME}/${S3_PREFIX}/" \
        --region "$AWS_REGION" \
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

    local s3_key="${S3_PREFIX}/${backup_name}"
    local output_file="${output_dir}/${backup_name}"

    mkdir -p "$output_dir"

    echo -e "${BLUE}Downloading backup from S3...${NC}"
    echo -e "  Key: $s3_key"
    echo -e "  Output: $output_file"
    echo ""

    if aws s3 cp "s3://${S3_BUCKET_NAME}/${s3_key}" "$output_file" \
        --region "$AWS_REGION"; then
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

    local s3_key="${S3_PREFIX}/${backup_name}"

    echo -e "${YELLOW}Warning: This will permanently delete the backup from S3${NC}"
    echo -e "  Key: $s3_key"
    read -p "Are you sure? (yes/no): " confirm

    if [ "$confirm" != "yes" ]; then
        echo "Cancelled"
        return 0
    fi

    if aws s3 rm "s3://${S3_BUCKET_NAME}/${s3_key}" \
        --region "$AWS_REGION"; then
        echo -e "${GREEN}✓ Backup deleted successfully!${NC}"
        return 0
    else
        echo -e "${RED}✗ Delete failed${NC}"
        return 1
    fi
}

# Function to sync local backups to S3
sync_backups() {
    local backup_dir="${PROJECT_DIR}/backups"

    if [ ! -d "$backup_dir" ]; then
        echo -e "${RED}Error: Backup directory not found: $backup_dir${NC}"
        exit 1
    fi

    echo -e "${BLUE}Syncing local backups to S3...${NC}"
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
    echo -e "${GREEN}✓ Synced $count backup(s) to S3${NC}"
}

# Function to test S3 connection
test_connection() {
    echo -e "${BLUE}Testing S3 connection...${NC}"
    echo ""

    # Test bucket access
    if aws s3 ls "s3://${S3_BUCKET_NAME}/" \
        --region "$AWS_REGION" >/dev/null 2>&1; then
        echo -e "${GREEN}✓ S3 connection successful!${NC}"
        echo ""
        echo "Configuration:"
        echo "  Region: $AWS_REGION"
        echo "  Bucket: $S3_BUCKET_NAME"
        echo "  Prefix: $S3_PREFIX"
        echo "  Storage Class: ${S3_STORAGE_CLASS:-STANDARD}"
        return 0
    else
        echo -e "${RED}✗ S3 connection failed${NC}"
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
            echo -e "${BLUE}AWS S3 Backup Manager${NC}"
            echo ""
            echo "Usage: $0 {upload|download|list|delete|sync|test|help} [options]"
            echo ""
            echo "Commands:"
            echo "  upload <file>           - Upload backup file to S3"
            echo "  download <name> [dir]   - Download backup from S3"
            echo "  list                   - List backups in S3"
            echo "  delete <name>          - Delete backup from S3"
            echo "  sync                   - Sync all local backups to S3"
            echo "  test                   - Test S3 connection"
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

