# How to Ensure You're Using the Latest Docker Image

This guide shows you how to check, pull, and automatically update to the latest Docker image on your Raspberry Pi 5.

## Quick Check: What Image Am I Using?

### Check Current Image

```bash
# See what image your container is using
docker inspect minecraft-server --format='{{.Config.Image}}'

# See when the image was created
docker images ghcr.io/and3rn3t/minecraft-server:latest --format "table {{.Repository}}\t{{.Tag}}\t{{.CreatedAt}}"

# See container status
docker ps -a | grep minecraft-server
```

### Check Image Digest (Most Accurate)

```bash
# Get the digest of the image you're currently using
docker inspect minecraft-server --format='{{.Image}}'

# Compare with what's in the registry
docker manifest inspect ghcr.io/and3rn3t/minecraft-server:latest | grep -A 1 digest
```

## Method 1: Manual Update (Immediate)

### Step 1: Pull Latest Image

```bash
cd ~/minecraft-server

# Pull the latest image from registry
docker compose pull

# Or if using docker directly
docker pull ghcr.io/and3rn3t/minecraft-server:latest
```

### Step 2: Restart Container with New Image

```bash
# Stop current container
docker compose down

# Start with new image (will use latest)
docker compose up -d

# Or force recreate
docker compose up -d --force-recreate
```

### Step 3: Verify New Image

```bash
# Check container is running
docker ps | grep minecraft-server

# Check logs to confirm it started with new image
docker logs minecraft-server --tail 20
```

## Method 2: Automatic Updates (Recommended)

### Option A: Use Systemd Service (Pulls on Start)

The `minecraft.service` already pulls the latest image before starting:

```bash
# Check if service is installed
sudo systemctl status minecraft.service

# Restart service (will pull latest image)
sudo systemctl restart minecraft.service

# Or reload (pulls and recreates)
sudo systemctl reload minecraft.service
```

### Option B: Use Auto-Update Timer (Periodic Checks)

Set up automatic updates every hour:

```bash
# Install update service and timer
sudo cp systemd/minecraft-update.service /etc/systemd/system/
sudo cp systemd/minecraft-update.timer /etc/systemd/system/

# Enable and start timer
sudo systemctl daemon-reload
sudo systemctl enable minecraft-update.timer
sudo systemctl start minecraft-update.timer

# Check timer status
sudo systemctl status minecraft-update.timer

# View when next update will run
sudo systemctl list-timers minecraft-update.timer
```

**What this does:**

- Checks for new image every hour
- Pulls latest image if available
- Restarts container with new image
- Logs updates to `/var/log/minecraft-update.log`

## Method 3: Use Pull Policy (Always Check)

Update your `docker-compose.yml` to always pull on start:

```yaml
services:
  minecraft:
    image: ghcr.io/and3rn3t/minecraft-server:latest
    pull_policy: always # Always check for updates
    # ... rest of config
```

Then every time you start:

```bash
docker compose up -d
```

It will automatically pull the latest image if available.

## Verify You Have the Latest Image

### Compare Image Digests

```bash
# Get digest of local image
LOCAL_DIGEST=$(docker inspect ghcr.io/and3rn3t/minecraft-server:latest --format='{{.RepoDigests}}' | cut -d'@' -f2 | cut -d']' -f1)

# Get digest from registry (requires authentication)
REGISTRY_DIGEST=$(docker manifest inspect ghcr.io/and3rn3t/minecraft-server:latest | grep -oP '"digest":\s*"\K[^"]+')

# Compare
if [ "$LOCAL_DIGEST" = "$REGISTRY_DIGEST" ]; then
    echo "✅ You have the latest image!"
else
    echo "⚠️  Image is outdated. Run: docker compose pull"
fi
```

### Check Image Build Date

```bash
# See when your local image was created
docker images ghcr.io/and3rn3t/minecraft-server:latest --format "Created: {{.CreatedAt}}"

# Compare with GitHub Actions (check latest commit time on main branch)
# Or check registry metadata
```

### Simple Check Script

Create `scripts/check-image-update.sh`:

```bash
#!/bin/bash
echo "Checking for image updates..."

# Pull without downloading (dry run)
docker pull ghcr.io/and3rn3t/minecraft-server:latest 2>&1 | grep -q "Image is up to date"

if [ $? -eq 0 ]; then
    echo "✅ You have the latest image"
else
    echo "⚠️  New image available! Run: docker compose pull && docker compose up -d"
fi
```

## Troubleshooting

### Authentication Issues

If you get authentication errors:

```bash
# Login to GitHub Container Registry
echo "YOUR_GITHUB_TOKEN" | docker login ghcr.io -u and3rn3t --password-stdin

# Or use your GitHub username and Personal Access Token
docker login ghcr.io
```

### Image Not Found

If image doesn't exist in registry:

1. Check CI workflow ran successfully
2. Verify image was pushed: `ghcr.io/and3rn3t/minecraft-server:latest`
3. Check GitHub Actions logs

### Container Won't Start with New Image

```bash
# Check logs
docker logs minecraft-server

# Check if old container is still running
docker ps -a

# Force remove and recreate
docker compose down
docker compose up -d --force-recreate
```

## Best Practices

### 1. Always Use Registry Images in Production

```yaml
# docker-compose.yml
services:
  minecraft:
    image: ghcr.io/and3rn3t/minecraft-server:latest
    pull_policy: always
```

### 2. Set Up Auto-Updates

Use the systemd timer for automatic updates:

```bash
sudo systemctl enable minecraft-update.timer
```

### 3. Monitor Updates

Check update logs:

```bash
# View update history
tail -f /var/log/minecraft-update.log

# Check when last update ran
sudo systemctl status minecraft-update.service
```

### 4. Test Before Production

```bash
# Pull and test in a separate container
docker run --rm ghcr.io/and3rn3t/minecraft-server:latest echo "Image works!"

# Or test with a different tag first
docker pull ghcr.io/and3rn3t/minecraft-server:main
docker compose -f docker-compose.test.yml up -d
```

## Quick Reference

```bash
# Check current image
docker inspect minecraft-server --format='{{.Config.Image}}'

# Pull latest
docker compose pull

# Update and restart
docker compose pull && docker compose up -d --force-recreate

# Check for updates (dry run)
docker pull ghcr.io/and3rn3t/minecraft-server:latest

# View update logs
tail -f /var/log/minecraft-update.log

# Manual update via systemd
sudo systemctl reload minecraft.service
```

## Summary

**To ensure you're always using the latest image:**

1. ✅ **Use registry-based docker-compose.yml** (not local build)
2. ✅ **Set `pull_policy: always`** in docker-compose.yml
3. ✅ **Enable auto-update timer** for periodic checks
4. ✅ **Manually pull** when you want immediate updates

The easiest setup is using the systemd timer which checks every hour and automatically updates when a new image is available.
