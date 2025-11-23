# Creating a Custom Raspberry Pi OS Image

This guide explains how to create a pre-configured Raspberry Pi OS `.img` file that includes Docker, Docker Compose, and the Minecraft server repository, ready to flash with Raspberry Pi Imager.

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Method 1: Using Raspberry Pi Imager Custom Image](#method-1-using-raspberry-pi-imager-custom-image)
4. [Method 2: Manual Image Creation](#method-2-manual-image-creation)
5. [Method 3: Automated Script](#method-3-automated-script)
6. [Using the Custom Image](#using-the-custom-image)
7. [Troubleshooting](#troubleshooting)

## Overview

A custom Raspberry Pi OS image allows you to:

- ✅ Pre-install Docker and Docker Compose
- ✅ Pre-clone the Minecraft server repository
- ✅ Pre-configure system settings
- ✅ Skip manual setup steps
- ✅ Distribute a ready-to-use image

**Note**: Custom images are typically 2-4GB in size and can be flashed directly to microSD cards.

## Prerequisites

### Required Software

- **Raspberry Pi Imager** (latest version)
  - Download: <https://www.raspberrypi.com/software/>
- **Linux system** (for manual/automated methods)
  - Ubuntu/Debian recommended
  - Or use WSL2 on Windows
  - Or use a Raspberry Pi itself

### Required Tools (Linux)

```bash
# Install required tools
sudo apt-get update
sudo apt-get install -y \
    wget \
    unzip \
    qemu-user-static \
    binfmt-support \
    kpartx \
    dosfstools \
    parted \
    git
```

### Disk Space

- **Minimum**: 8GB free space
- **Recommended**: 16GB+ free space
- For the image file and working directories

## Method 1: Using Raspberry Pi Imager Custom Image

Raspberry Pi Imager supports custom images through the "Use custom image" option.

### Step 1: Prepare the Base Image

1. Download Raspberry Pi OS (64-bit) image:
   - Visit: <https://www.raspberrypi.com/software/operating-systems/>
   - Download: "Raspberry Pi OS (64-bit)" (not Lite)
   - Extract the `.img` file

### Step 2: Flash and Configure

1. Flash the image to a microSD card using Raspberry Pi Imager
2. Boot the Raspberry Pi 5
3. Run the setup script (see [INSTALL.md](INSTALL.md))
4. Shut down the Raspberry Pi cleanly

### Step 3: Create Image from Configured Card

1. Insert the configured microSD card into your computer
2. Use `dd` or imaging tool to create an image:

```bash
# On Linux/macOS
sudo dd if=/dev/sdX of=minecraft-server-rpi5.img bs=4M status=progress

# Replace /dev/sdX with your SD card device
# Use: lsblk or diskutil list to find the device
```

3. Compress the image (optional but recommended):

```bash
# Compress to save space
gzip minecraft-server-rpi5.img

# Results in: minecraft-server-rpi5.img.gz
```

### Step 4: Use Custom Image

1. Open Raspberry Pi Imager
2. Click "Choose OS" → Scroll down → "Use custom image"
3. Select your `.img` or `.img.gz` file
4. Choose storage device
5. Click "Write"

**Limitations**: This method requires physical access to a Raspberry Pi 5.

## Method 2: Manual Image Creation

Create a custom image without needing a physical Raspberry Pi.

### Step 1: Download Base Image

```bash
# Create working directory
mkdir -p ~/rpi-image-build
cd ~/rpi-image-build

# Download Raspberry Pi OS (64-bit)
wget https://downloads.raspberrypi.com/raspios_arm64/images/raspios_arm64-YYYY-MM-DD/YYYY-MM-DD-raspios-bookworm-arm64.img.xz

# Extract
unxz YYYY-MM-DD-raspios-bookworm-arm64.img.xz
```

### Step 2: Mount the Image

```bash
# Set variables
IMAGE_FILE="YYYY-MM-DD-raspios-bookworm-arm64.img"
MOUNT_POINT="/mnt/rpi"

# Create mount point
sudo mkdir -p "$MOUNT_POINT"

# Get partition info
sudo fdisk -l "$IMAGE_FILE"

# Note the start sector of the root partition (usually second partition)
# Example output: /dev/loop0p2 starts at sector 532480

# Create loop device
LOOP_DEV=$(sudo losetup -fP --show "$IMAGE_FILE")

# Mount root partition
sudo mount "${LOOP_DEV}p2" "$MOUNT_POINT"
sudo mount "${LOOP_DEV}p1" "$MOUNT_POINT/boot"
```

### Step 3: Configure Image

```bash
# Enable QEMU for ARM emulation
sudo cp /usr/bin/qemu-aarch64-static "$MOUNT_POINT/usr/bin/"

# Mount required filesystems
sudo mount --bind /dev "$MOUNT_POINT/dev"
sudo mount --bind /sys "$MOUNT_POINT/sys"
sudo mount --bind /proc "$MOUNT_POINT/proc"
sudo mount --bind /dev/pts "$MOUNT_POINT/dev/pts"

# Chroot into the image
sudo chroot "$MOUNT_POINT" /bin/bash
```

### Step 4: Install Software (Inside Chroot)

```bash
# Update package list
apt-get update

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
rm get-docker.sh

# Install Docker Compose
apt-get install -y docker-compose

# Install additional tools
apt-get install -y git wget curl screen htop python3 python3-pip

# Install Node.js (for web interface)
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
apt-get install -y nodejs

# Clone repository
cd /home/pi
git clone https://github.com/and3rn3t/minecraft.git minecraft-server

# Set permissions
chown -R pi:pi /home/pi/minecraft-server

# Add user to docker group
usermod -aG docker pi

# Clean up
apt-get clean
rm -rf /var/lib/apt/lists/*
rm -rf /tmp/*

# Exit chroot
exit
```

### Step 5: Configure First Boot

```bash
# Create first-boot script
sudo tee "$MOUNT_POINT/home/pi/first-boot.sh" > /dev/null << 'EOF'
#!/bin/bash
cd ~/minecraft-server
chmod +x setup-rpi.sh manage.sh scripts/*.sh
# Optional: Run setup if needed
# ./setup-rpi.sh
EOF

sudo chmod +x "$MOUNT_POINT/home/pi/first-boot.sh"
sudo chown pi:pi "$MOUNT_POINT/home/pi/first-boot.sh"

# Add to .bashrc or create systemd service for first boot
```

### Step 6: Unmount and Finalize

```bash
# Exit chroot if still inside
exit

# Unmount filesystems
sudo umount "$MOUNT_POINT/dev/pts"
sudo umount "$MOUNT_POINT/proc"
sudo umount "$MOUNT_POINT/sys"
sudo umount "$MOUNT_POINT/dev"
sudo umount "$MOUNT_POINT/boot"
sudo umount "$MOUNT_POINT"

# Remove loop device
sudo losetup -d "$LOOP_DEV"

# Remove QEMU binary from image
# (It will be re-added on next mount if needed)

# Compress image
gzip "$IMAGE_FILE"
```

## Method 3: Automated Script

Use the provided script to automate the process.

### Step 1: Run the Script

```bash
# Clone repository (if not already)
git clone https://github.com/and3rn3t/minecraft.git
cd minecraft/scripts

# Make script executable
chmod +x create-custom-image.sh

# Run the script
sudo ./create-custom-image.sh
```

### Step 2: Follow Prompts

The script will:

1. Download Raspberry Pi OS image (if not present)
2. Mount the image
3. Install Docker, Docker Compose, and dependencies
4. Clone the repository
5. Configure the system
6. Create the final image file

### Step 3: Output

The script creates:

- `minecraft-server-rpi5-YYYYMMDD.img` - Final image file
- `minecraft-server-rpi5-YYYYMMDD.img.gz` - Compressed version

## Using the Custom Image

### With Raspberry Pi Imager

1. Open Raspberry Pi Imager
2. Click "Choose OS" → "Use custom image"
3. Select your `.img` or `.img.gz` file
4. Click "Choose Storage" → Select microSD card
5. Click "Write"
6. Wait for completion

### With Command Line (Linux)

```bash
# Uncompress if needed
gunzip minecraft-server-rpi5-YYYYMMDD.img.gz

# Write to SD card
sudo dd if=minecraft-server-rpi5-YYYYMMDD.img of=/dev/sdX bs=4M status=progress conv=fsync

# Replace /dev/sdX with your SD card device
# Use: lsblk to find the device
```

### First Boot

1. Insert microSD card into Raspberry Pi 5
2. Power on
3. Wait for first boot (2-3 minutes)
4. SSH into the Pi:

```bash
ssh pi@minecraft-server.local
# Or use IP address
```

5. Navigate to server directory:

```bash
cd ~/minecraft-server
```

6. Start the server:

```bash
./manage.sh start
```

## Image Customization

### Pre-configure Settings

Edit files before finalizing the image:

```bash
# Server properties
sudo nano "$MOUNT_POINT/home/pi/minecraft-server/server.properties"

# Docker Compose settings
sudo nano "$MOUNT_POINT/home/pi/minecraft-server/docker-compose.yml"

# Environment variables
sudo nano "$MOUNT_POINT/home/pi/minecraft-server/.env"
```

### Add Custom Scripts

```bash
# Copy custom scripts
sudo cp custom-script.sh "$MOUNT_POINT/home/pi/minecraft-server/scripts/"
sudo chown pi:pi "$MOUNT_POINT/home/pi/minecraft-server/scripts/custom-script.sh"
```

### Pre-install Plugins

```bash
# Copy plugin JARs
sudo mkdir -p "$MOUNT_POINT/home/pi/minecraft-server/plugins"
sudo cp plugin.jar "$MOUNT_POINT/home/pi/minecraft-server/plugins/"
sudo chown -R pi:pi "$MOUNT_POINT/home/pi/minecraft-server/plugins"
```

## Troubleshooting

### Image Too Large

**Issue**: Image file is larger than expected.

**Solution**:

```bash
# Shrink the image before finalizing
sudo resize2fs -M "$MOUNT_POINT"
sudo fdisk "$IMAGE_FILE"  # Resize partition
```

### Cannot Mount Image

**Issue**: Mount fails with permission errors.

**Solution**:

```bash
# Ensure you're using sudo
sudo mount ...

# Check if loop device is available
sudo losetup -f

# Check partition table
sudo fdisk -l "$IMAGE_FILE"
```

### Chroot Fails

**Issue**: Commands fail inside chroot.

**Solution**:

```bash
# Ensure QEMU is copied
sudo cp /usr/bin/qemu-aarch64-static "$MOUNT_POINT/usr/bin/"

# Mount all required filesystems
sudo mount --bind /dev "$MOUNT_POINT/dev"
sudo mount --bind /sys "$MOUNT_POINT/sys"
sudo mount --bind /proc "$MOUNT_POINT/proc"
```

### Image Doesn't Boot

**Issue**: Raspberry Pi doesn't boot from custom image.

**Solution**:

- Verify image was written correctly: `sudo fdisk -l /dev/sdX`
- Check boot partition is FAT32: `sudo file -s /dev/sdX1`
- Ensure Raspberry Pi 5 is selected in Imager
- Try re-flashing the image

### Docker Not Working

**Issue**: Docker commands fail after boot.

**Solution**:

```bash
# Re-add user to docker group
sudo usermod -aG docker pi

# Restart Docker service
sudo systemctl restart docker

# Log out and back in
exit
ssh pi@minecraft-server.local
```

## Best Practices

### 1. Version Your Images

```bash
# Include date and version in filename
minecraft-server-rpi5-20250115-v1.0.img
```

### 2. Document Changes

Keep a changelog of what's included in each image version.

### 3. Test Before Distribution

Always test the image on actual hardware before sharing.

### 4. Compress Images

```bash
# Compress to save space
gzip minecraft-server-rpi5.img
# Reduces size by ~50-70%
```

### 5. Verify Checksums

```bash
# Create checksum
sha256sum minecraft-server-rpi5.img > minecraft-server-rpi5.img.sha256

# Verify later
sha256sum -c minecraft-server-rpi5.img.sha256
```

## Security Considerations

### 1. Change Default Passwords

Always change default passwords before distributing images.

### 2. Remove Sensitive Data

```bash
# Clear bash history
sudo rm "$MOUNT_POINT/home/pi/.bash_history"

# Remove SSH keys (users will generate new ones)
sudo rm -rf "$MOUNT_POINT/home/pi/.ssh"
```

### 3. Update Before Distribution

```bash
# Update all packages
apt-get update && apt-get upgrade -y
```

## Distribution

### Hosting Options

- **GitHub Releases**: Upload `.img.gz` files
- **Cloud Storage**: Google Drive, Dropbox, etc.
- **File Server**: Host on your own server
- **Torrent**: For large distributions

### File Naming Convention

```
minecraft-server-rpi5-YYYYMMDD-vX.Y.img.gz
```

Example: `minecraft-server-rpi5-20250115-v1.0.img.gz`

## Quick Reference

### Automated Script (Recommended)

```bash
# On Linux system with sudo access
cd scripts
sudo ./create-custom-image.sh
```

The script will:

1. Download Raspberry Pi OS image (if needed)
2. Mount and configure the image
3. Install Docker, Docker Compose, and dependencies
4. Clone the Minecraft server repository
5. Create final `.img` and `.img.gz` files

### Manual Process

1. **Download base image**: Raspberry Pi OS (64-bit)
2. **Mount image**: Use loop device and mount partitions
3. **Chroot and configure**: Install software inside chroot
4. **Unmount**: Clean up and create final image
5. **Compress**: Create `.img.gz` for distribution

### Using the Image

1. Open Raspberry Pi Imager
2. Choose OS → "Use custom image"
3. Select your `.img` or `.img.gz` file
4. Choose storage device
5. Click "Write"

## See Also

- [Raspberry Pi Image Preparation](RASPBERRY_PI_IMAGE_PREPARATION.md) - Manual setup guide
- [Installation Guide](INSTALL.md) - Standard installation
- [Building Docker Image](BUILDING_RPI5_IMAGE.md) - Docker image creation
- [Raspberry Pi Imager Documentation](https://www.raspberrypi.com/documentation/computers/getting-started.html#using-raspberry-pi-imager)
