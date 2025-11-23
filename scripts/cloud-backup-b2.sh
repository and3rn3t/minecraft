#!/bin/bash
# Backblaze B2 Backup Script
# Uploads and restores backups from Backblaze B2

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
CONFIG_FILE="${PROJECT_DIR}/config/cloud-backup-b2.conf"

# Load configuration
if [ -f "$CONFIG_FILE" ]; then
    source "$CONFIG_FILE"
else
    echo -e "${YELLOW}Config file not found: $CONFIG_FILE${NC}"
    echo "Creating example config..."
    mkdir -p "$(dirname "$CONFIG_FILE")"
    cat > "$CONFIG_FILE" << 'EOF'
# Backblaze B2 Backup Configuration
# Copy this to config/cloud-backup-b2.conf and fill in your credentials

# B2 Application Key ID
# Create in B2 dashboard: App Keys > Add a New Application Key
B2_KEY_ID=""

# B2 Application Key
# Keep this secret! Never commit this file to git.
B2_APPLICATION_KEY=""

# B2 Bucket Name
B2_BUCKET_NAME=""

# B2 Bucket ID (optional, will be looked up if not provided)
B2_BUCKET_ID=""

# Backup prefix in bucket (optional)
# All backups will be stored under this prefix
B2_PREFIX="minecraft-backups"

# Auto-upload after local backup (optional)
AUTO_UPLOAD="false"

# Auto-delete local after upload (optional, use with caution)
AUTO_DELETE_LOCAL="false"
EOF
    echo -e "${GREEN}Example config created: $CONFIG_FILE${NC}"
    echo "Please edit the config file with your B2 credentials"
    exit 1
fi

# Check required configuration
if [ -z "$B2_KEY_ID" ] || [ -z "$B2_APPLICATION_KEY" ] || [ -z "$B2_BUCKET_NAME" ]; then
    echo -e "${RED}Error: B2 configuration incomplete${NC}"
    echo "Please configure $CONFIG_FILE with your B2 credentials"
    exit 1
fi

# Check for B2 CLI
if ! command -v b2 >/dev/null 2>&1; then
    echo -e "${YELLOW}B2 CLI not found. Installing...${NC}"
    echo "Install with: pip install b2sdk"
    echo "Or download from: https://www.backblaze.com/b2/docs/quick_command_line.html"
    exit 1
fi

# Function to authorize B2
authorize_b2() {
    if [ -z "$B2_KEY_ID" ] || [ -z "$B2_APPLICATION_KEY" ]; then
        echo -e "${RED}Error: B2 credentials not configured${NC}"
        exit 1
    fi

    # Authorize with B2
    b2 authorize-account "$B2_KEY_ID" "$B2_APPLICATION_KEY" >/dev/null 2>&1
}

# Function to get bucket ID
get_bucket_id() {
    if [ -n "$B2_BUCKET_ID" ]; then
        echo "$B2_BUCKET_ID"
        return 0
    fi

    # Look up bucket ID
    local bucket_id=$(b2 list-buckets | grep "$B2_BUCKET_NAME" | awk '{print $1}' | head -1)
    echo "$bucket_id"
}

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

    authorize_b2

    local backup_name=$(basename "$backup_file")
    local b2_key="${B2_PREFIX}/${backup_name}"
    local bucket_id=$(get_bucket_id)

    if [ -z "$bucket_id" ]; then
        echo -e "${RED}Error: Could not find bucket ID for $B2_BUCKET_NAME${NC}"
        exit 1
    fi

    echo -e "${BLUE}Uploading backup to B2...${NC}"
    echo -e "  File: $backup_file"
    echo -e "  Key: $b2_key"
    echo -e "  Bucket: $B2_BUCKET_NAME (ID: $bucket_id)"
    echo ""

    # Upload using B2 CLI
    if b2 upload-file "$bucket_id" "$backup_file" "$b2_key"; then
        echo -e "${GREEN}✓ Backup uploaded successfully!${NC}"
        echo ""
        echo "B2 File: $b2_key"
        return 0
    else
        echo -e "${RED}✗ Upload failed${NC}"
        return 1
    fi
}

# Function to list backups
list_backups() {
    authorize_b2

    local bucket_id=$(get_bucket_id)

    if [ -z "$bucket_id" ]; then
        echo -e "${RED}Error: Could not find bucket ID for $B2_BUCKET_NAME${NC}"
        exit 1
    fi

    echo -e "${BLUE}Listing backups in B2...${NC}"
    echo ""

    b2 list-file-names "$bucket_id" "$B2_PREFIX/" | while IFS= read -r line; do
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

    authorize_b2

    local bucket_id=$(get_bucket_id)

    if [ -z "$bucket_id" ]; then
        echo -e "${RED}Error: Could not find bucket ID for $B2_BUCKET_NAME${NC}"
        exit 1
    fi

    local b2_key="${B2_PREFIX}/${backup_name}"
    local output_file="${output_dir}/${backup_name}"

    mkdir -p "$output_dir"

    echo -e "${BLUE}Downloading backup from B2...${NC}"
    echo -e "  Key: $b2_key"
    echo -e "  Output: $output_file"
    echo ""

    if b2 download-file-by-name "$bucket_id" "$b2_key" "$output_file"; then
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

    authorize_b2

    local bucket_id=$(get_bucket_id)

    if [ -z "$bucket_id" ]; then
        echo -e "${RED}Error: Could not find bucket ID for $B2_BUCKET_NAME${NC}"
        exit 1
    fi

    local b2_key="${B2_PREFIX}/${backup_name}"

    # Get file ID first
    local file_id=$(b2 list-file-names "$bucket_id" "$b2_key" | awk '{print $1}' | head -1)

    if [ -z "$file_id" ]; then
        echo -e "${RED}Error: Backup not found: $b2_key${NC}"
        exit 1
    fi

    echo -e "${YELLOW}Warning: This will permanently delete the backup from B2${NC}"
    echo -e "  Key: $b2_key"
    echo -e "  File ID: $file_id"
    read -p "Are you sure? (yes/no): " confirm

    if [ "$confirm" != "yes" ]; then
        echo "Cancelled"
        return 0
    fi

    if b2 delete-file-version "$file_id" "$b2_key"; then
        echo -e "${GREEN}✓ Backup deleted successfully!${NC}"
        return 0
    else
        echo -e "${RED}✗ Delete failed${NC}"
        return 1
    fi
}

# Function to sync local backups to B2
sync_backups() {
    local backup_dir="${PROJECT_DIR}/backups"

    if [ ! -d "$backup_dir" ]; then
        echo -e "${RED}Error: Backup directory not found: $backup_dir${NC}"
        exit 1
    fi

    echo -e "${BLUE}Syncing local backups to B2...${NC}"
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
    echo -e "${GREEN}✓ Synced $count backup(s) to B2${NC}"
}

# Function to test B2 connection
test_connection() {
    echo -e "${BLUE}Testing B2 connection...${NC}"
    echo ""

    authorize_b2

    local bucket_id=$(get_bucket_id)

    if [ -n "$bucket_id" ]; then
        echo -e "${GREEN}✓ B2 connection successful!${NC}"
        echo ""
        echo "Configuration:"
        echo "  Bucket: $B2_BUCKET_NAME"
        echo "  Bucket ID: $bucket_id"
        echo "  Prefix: $B2_PREFIX"
        return 0
    else
        echo -e "${RED}✗ B2 connection failed${NC}"
        echo "Please check your credentials and bucket name"
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
            echo -e "${BLUE}Backblaze B2 Backup Manager${NC}"
            echo ""
            echo "Usage: $0 {upload|download|list|delete|sync|test|help} [options]"
            echo ""
            echo "Commands:"
            echo "  upload <file>           - Upload backup file to B2"
            echo "  download <name> [dir]   - Download backup from B2"
            echo "  list                   - List backups in B2"
            echo "  delete <name>          - Delete backup from B2"
            echo "  sync                   - Sync all local backups to B2"
            echo "  test                   - Test B2 connection"
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
            echo "Note: Install B2 CLI with: pip install b2sdk"
            echo ""
            exit 1
            ;;
    esac
}

# Run main function
main "$@"

