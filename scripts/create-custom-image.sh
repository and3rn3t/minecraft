#!/bin/bash
# Create Custom Raspberry Pi OS Image for Minecraft Server
# This script creates a pre-configured Raspberry Pi OS image with Docker and the Minecraft server
#
# Usage: sudo ./create-custom-image.sh
#
# Requirements:
# - Run on Linux (Ubuntu/Debian recommended)
# - Root/sudo access
# - 16GB+ free disk space
# - Internet connection

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Configuration
WORK_DIR="${WORK_DIR:-$HOME/rpi-image-build}"
IMAGE_NAME="${IMAGE_NAME:-minecraft-server-rpi5}"
REPO_URL="${REPO_URL:-https://github.com/and3rn3t/minecraft.git}"
RPI_OS_URL="${RPI_OS_URL:-https://downloads.raspberrypi.com/raspios_arm64/images/raspios_arm64-2024-07-04/2024-07-04-raspios-bookworm-arm64.img.xz}"

# Function to print header
print_header() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
}

# Function to check prerequisites
check_prerequisites() {
    print_header "Checking Prerequisites"

    # Check if running as root
    if [ "$EUID" -ne 0 ]; then
        echo -e "${RED}Error: This script must be run as root (use sudo)${NC}"
        exit 1
    fi

    # Check required tools
    local missing_tools=()
    for tool in wget unzip qemu-aarch64-static kpartx dosfstools parted git; do
        if ! command -v "$tool" &> /dev/null; then
            missing_tools+=("$tool")
        fi
    done

    if [ ${#missing_tools[@]} -ne 0 ]; then
        echo -e "${YELLOW}Installing missing tools: ${missing_tools[*]}${NC}"
        apt-get update
        apt-get install -y "${missing_tools[@]}"
    fi

    # Check for QEMU
    if [ ! -f /usr/bin/qemu-aarch64-static ]; then
        echo -e "${YELLOW}Installing QEMU...${NC}"
        apt-get install -y qemu-user-static binfmt-support
    fi

    # Check disk space
    local available_space=$(df -BG "$WORK_DIR" 2>/dev/null | tail -1 | awk '{print $4}' | sed 's/G//')
    if [ -z "$available_space" ] || [ "$available_space" -lt 16 ]; then
        echo -e "${YELLOW}Warning: Less than 16GB free space available${NC}"
        echo -e "${YELLOW}Continuing anyway, but may run out of space${NC}"
    fi

    echo -e "${GREEN}Prerequisites check complete${NC}"
    echo ""
}

# Function to download Raspberry Pi OS image
download_image() {
    print_header "Downloading Raspberry Pi OS Image"

    mkdir -p "$WORK_DIR"
    cd "$WORK_DIR"

    # Check if image already exists
    local img_file=$(find . -name "*.img" -type f 2>/dev/null | head -1)
    if [ -n "$img_file" ]; then
        echo -e "${YELLOW}Found existing image: $img_file${NC}"
        read -p "Use existing image? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            IMAGE_FILE="$img_file"
            return
        fi
    fi

    # Download image
    echo -e "${BLUE}Downloading Raspberry Pi OS image...${NC}"
    echo -e "${YELLOW}This may take a while (2-4GB download)${NC}"

    wget -c "$RPI_OS_URL" -O raspios.img.xz || {
        echo -e "${RED}Error: Failed to download image${NC}"
        echo -e "${YELLOW}Please download manually and place .img file in $WORK_DIR${NC}"
        exit 1
    }

    # Extract
    echo -e "${BLUE}Extracting image...${NC}"
    unxz raspios.img.xz || {
        echo -e "${RED}Error: Failed to extract image${NC}"
        exit 1
    }

    IMAGE_FILE=$(find . -name "*.img" -type f | head -1)
    echo -e "${GREEN}Image ready: $IMAGE_FILE${NC}"
    echo ""
}

# Function to setup loop device and mount
setup_mount() {
    print_header "Setting Up Image Mount"

    # Create loop device
    LOOP_DEV=$(losetup -fP --show "$IMAGE_FILE")
    echo -e "${GREEN}Loop device: $LOOP_DEV${NC}"

    # Wait for partitions
    sleep 2
    partprobe "$LOOP_DEV" || true

    # Create mount point
    MOUNT_POINT="/mnt/rpi-custom"
    mkdir -p "$MOUNT_POINT"

    # Mount partitions
    echo -e "${BLUE}Mounting partitions...${NC}"
    mount "${LOOP_DEV}p2" "$MOUNT_POINT" || {
        echo -e "${RED}Error: Failed to mount root partition${NC}"
        exit 1
    }
    mount "${LOOP_DEV}p1" "$MOUNT_POINT/boot" || {
        echo -e "${YELLOW}Warning: Failed to mount boot partition${NC}"
    }

    echo -e "${GREEN}Image mounted at: $MOUNT_POINT${NC}"
    echo ""
}

# Function to configure image
configure_image() {
    print_header "Configuring Image"

    # Copy QEMU for ARM emulation
    cp /usr/bin/qemu-aarch64-static "$MOUNT_POINT/usr/bin/" || {
        echo -e "${YELLOW}Warning: QEMU copy failed, continuing anyway${NC}"
    }

    # Mount required filesystems
    mount --bind /dev "$MOUNT_POINT/dev"
    mount --bind /sys "$MOUNT_POINT/sys"
    mount --bind /proc "$MOUNT_POINT/proc"
    mount --bind /dev/pts "$MOUNT_POINT/dev/pts"

    # Update package list
    echo -e "${BLUE}Updating package list...${NC}"
    chroot "$MOUNT_POINT" apt-get update

    # Install Docker
    echo -e "${BLUE}Installing Docker...${NC}"
    chroot "$MOUNT_POINT" bash -c "curl -fsSL https://get.docker.com -o /tmp/get-docker.sh && sh /tmp/get-docker.sh && rm /tmp/get-docker.sh"

    # Install Docker Compose
    echo -e "${BLUE}Installing Docker Compose...${NC}"
    chroot "$MOUNT_POINT" apt-get install -y docker-compose

    # Install additional tools
    echo -e "${BLUE}Installing additional tools...${NC}"
    chroot "$MOUNT_POINT" apt-get install -y \
        git \
        wget \
        curl \
        screen \
        htop \
        python3 \
        python3-pip \
        python3-venv

    # Install Node.js
    echo -e "${BLUE}Installing Node.js...${NC}"
    chroot "$MOUNT_POINT" bash -c "curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && apt-get install -y nodejs"

    # Add user to docker group
    echo -e "${BLUE}Configuring Docker permissions...${NC}"
    chroot "$MOUNT_POINT" usermod -aG docker pi

    # Clone repository
    echo -e "${BLUE}Cloning Minecraft server repository...${NC}"
    chroot "$MOUNT_POINT" bash -c "cd /home/pi && git clone $REPO_URL minecraft-server || true"

    # Set permissions
    chroot "$MOUNT_POINT" chown -R pi:pi /home/pi/minecraft-server

    # Make scripts executable
    chroot "$MOUNT_POINT" bash -c "cd /home/pi/minecraft-server && chmod +x *.sh scripts/*.sh 2>/dev/null || true"

    # Create first-boot script
    echo -e "${BLUE}Creating first-boot script...${NC}"
    cat > "$MOUNT_POINT/home/pi/first-boot.sh" << 'FIRSTBOOT_EOF'
#!/bin/bash
# First boot script for Minecraft server
cd ~/minecraft-server
if [ -f "setup-rpi.sh" ]; then
    chmod +x setup-rpi.sh manage.sh scripts/*.sh 2>/dev/null || true
fi
echo "Minecraft server repository ready at ~/minecraft-server"
FIRSTBOOT_EOF

    chmod +x "$MOUNT_POINT/home/pi/first-boot.sh"
    chown pi:pi "$MOUNT_POINT/home/pi/first-boot.sh"

    # Clean up
    echo -e "${BLUE}Cleaning up...${NC}"
    chroot "$MOUNT_POINT" apt-get clean
    chroot "$MOUNT_POINT" rm -rf /var/lib/apt/lists/*
    chroot "$MOUNT_POINT" rm -rf /tmp/*

    # Remove QEMU (will be re-added if needed)
    rm -f "$MOUNT_POINT/usr/bin/qemu-aarch64-static"

    echo -e "${GREEN}Image configuration complete${NC}"
    echo ""
}

# Function to unmount image
unmount_image() {
    print_header "Unmounting Image"

    # Unmount filesystems
    umount "$MOUNT_POINT/dev/pts" 2>/dev/null || true
    umount "$MOUNT_POINT/proc" 2>/dev/null || true
    umount "$MOUNT_POINT/sys" 2>/dev/null || true
    umount "$MOUNT_POINT/dev" 2>/dev/null || true
    umount "$MOUNT_POINT/boot" 2>/dev/null || true
    umount "$MOUNT_POINT" 2>/dev/null || true

    # Remove loop device
    if [ -n "$LOOP_DEV" ]; then
        losetup -d "$LOOP_DEV" 2>/dev/null || true
    fi

    echo -e "${GREEN}Image unmounted${NC}"
    echo ""
}

# Function to create final image
create_final_image() {
    print_header "Creating Final Image"

    cd "$WORK_DIR"

    # Generate output filename with date
    DATE_STR=$(date +%Y%m%d)
    OUTPUT_FILE="${IMAGE_NAME}-${DATE_STR}.img"

    # Copy image
    echo -e "${BLUE}Creating final image: $OUTPUT_FILE${NC}"
    cp "$IMAGE_FILE" "$OUTPUT_FILE"

    # Create checksum
    echo -e "${BLUE}Creating checksum...${NC}"
    sha256sum "$OUTPUT_FILE" > "${OUTPUT_FILE}.sha256"

    # Compress
    echo -e "${BLUE}Compressing image (this may take a while)...${NC}"
    gzip -c "$OUTPUT_FILE" > "${OUTPUT_FILE}.gz"
    sha256sum "${OUTPUT_FILE}.gz" > "${OUTPUT_FILE}.gz.sha256"

    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}Image Creation Complete!${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo -e "${BLUE}Output files:${NC}"
    echo -e "  - ${OUTPUT_FILE} ($(du -h "$OUTPUT_FILE" | cut -f1))"
    echo -e "  - ${OUTPUT_FILE}.gz ($(du -h "${OUTPUT_FILE}.gz" | cut -f1))"
    echo -e "  - ${OUTPUT_FILE}.sha256"
    echo -e "  - ${OUTPUT_FILE}.gz.sha256"
    echo ""
    echo -e "${YELLOW}To use with Raspberry Pi Imager:${NC}"
    echo -e "  1. Open Raspberry Pi Imager"
    echo -e "  2. Choose OS → Use custom image"
    echo -e "  3. Select: ${OUTPUT_FILE}.gz"
    echo -e "  4. Choose storage device"
    echo -e "  5. Click Write"
    echo ""
}

# Function to cleanup on error
cleanup() {
    echo -e "${RED}Error occurred, cleaning up...${NC}"
    unmount_image
    exit 1
}

# Set trap for cleanup
trap cleanup ERR

# Main execution
main() {
    print_header "Custom Raspberry Pi OS Image Creator"
    echo -e "${BLUE}This script will create a pre-configured Raspberry Pi OS image${NC}"
    echo -e "${BLUE}with Docker and the Minecraft server repository.${NC}"
    echo ""
    read -p "Continue? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Aborted."
        exit 0
    fi

    check_prerequisites
    download_image
    setup_mount
    configure_image
    unmount_image
    create_final_image

    echo -e "${GREEN}All done!${NC}"
}

# Run main function
main "$@"

