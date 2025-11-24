# Automatic Docker Image Deployment Setup

This guide shows you how to set up automatic deployment so that when you push code to GitHub, the Docker image is automatically built, pushed to the registry, and pulled by your Raspberry Pi.

## Overview

**Complete Flow:**

```
Code Push → CI Builds Image → Push to GHCR → Pi Pulls & Restarts
```

## Prerequisites

1. GitHub repository with Actions enabled
2. Raspberry Pi with Docker installed
3. GitHub Personal Access Token (for Pi to pull images)

## Step 1: Enable Image Pushing in CI

The CI workflow is already configured to push images on `main` branch commits. Verify in `.github/workflows/main.yml`:

- ✅ Builds Docker image
- ✅ Pushes to `ghcr.io/and3rn3t/minecraft-server:latest` on main branch
- ✅ Uses GitHub token for authentication

**What happens:**

- Every push to `main` triggers a build
- Image is pushed to GitHub Container Registry
- Available at: `ghcr.io/and3rn3t/minecraft-server:latest`

## Step 2: Configure Raspberry Pi to Pull from Registry

### Option A: Use Registry-Based docker-compose.yml

1. **On your Raspberry Pi**, update `docker-compose.yml`:

```bash
cd ~/minecraft-server

# Backup current file
cp docker-compose.yml docker-compose.yml.local

# Use registry-based configuration
cp docker-compose.registry.yml docker-compose.yml
```

Or manually edit `docker-compose.yml` to change:

```yaml
# FROM:
services:
  minecraft:
    build:
      context: .
      dockerfile: Dockerfile

# TO:
services:
  minecraft:
    image: ghcr.io/and3rn3t/minecraft-server:latest
    pull_policy: always
```

### Option B: Keep Building Locally (Fallback)

If you want to keep building locally but have the option to pull:

```yaml
services:
  minecraft:
    # Try to pull first, fall back to building
    image: ghcr.io/and3rn3t/minecraft-server:latest
    pull_policy: always
    build:
      context: .
      dockerfile: Dockerfile
```

## Step 3: Set Up Registry Authentication

The Raspberry Pi needs to authenticate to pull from GitHub Container Registry.

### Create GitHub Personal Access Token

1. Go to GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Generate new token with:
   - **Name**: `Raspberry Pi Docker Pull`
   - **Expiration**: Choose appropriate (or no expiration)
   - **Scopes**: `read:packages` (minimum needed)

### Configure Docker Login on Pi

**Option A: Manual Login (One-time)**

```bash
# On Raspberry Pi
echo "YOUR_GITHUB_TOKEN" | docker login ghcr.io -u and3rn3t --password-stdin
```

**Option B: Store Token Securely**

```bash
# Create token file (restrict permissions)
echo "YOUR_GITHUB_TOKEN" | sudo tee /root/.docker/github_token
sudo chmod 600 /root/.docker/github_token

# Login using token file
cat /root/.docker/github_token | docker login ghcr.io -u and3rn3t --password-stdin
```

**Option C: Use Docker Credential Helper (Recommended)**

```bash
# Install credential helper
sudo apt-get install -y docker-credential-helpers

# Configure
mkdir -p ~/.docker
cat > ~/.docker/config.json << EOF
{
  "auths": {
    "ghcr.io": {}
  },
  "credsStore": "pass"
}
EOF

# Store token using pass (or use another credential helper)
```

## Step 4: Set Up Auto-Pull Service

### Install Systemd Service

1. **Copy service file to Pi:**

```bash
# On Raspberry Pi
cd ~/minecraft-server
sudo cp systemd/minecraft.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable minecraft.service
```

2. **Update service to use registry-based compose:**

Edit `/etc/systemd/system/minecraft.service` and ensure `WorkingDirectory` points to your minecraft-server directory.

### Option A: Pull Only on Boot

The service will pull the latest image when the Pi boots:

```bash
# Service is already configured to pull on start
sudo systemctl start minecraft.service
sudo systemctl status minecraft.service
```

### Option B: Periodic Auto-Updates (Recommended)

Set up a timer to periodically check for updates:

```bash
# Copy timer and service files
sudo cp systemd/minecraft-update.service /etc/systemd/system/
sudo cp systemd/minecraft-update.timer /etc/systemd/system/

# Enable and start timer
sudo systemctl daemon-reload
sudo systemctl enable minecraft-update.timer
sudo systemctl start minecraft-update.timer

# Check timer status
sudo systemctl status minecraft-update.timer
sudo systemctl list-timers | grep minecraft
```

**Timer Schedule:**

- Checks 5 minutes after boot
- Then checks every hour
- Random delay (0-5 min) to avoid thundering herd

## Step 5: Verify Deployment

### Test Manual Pull

```bash
# On Raspberry Pi
cd ~/minecraft-server
docker compose pull
docker compose up -d
```

### Check Image Source

```bash
# Verify image is from registry
docker images | grep minecraft-server

# Should show:
# ghcr.io/and3rn3t/minecraft-server   latest   ...
```

### Test Auto-Update

1. Push a commit to main branch
2. Wait for CI to build and push (check GitHub Actions)
3. On Pi, manually trigger update:

```bash
sudo systemctl start minecraft-update.service
```

Or wait for the timer (checks every hour).

## Complete Workflow Example

### Developer Workflow

```bash
# 1. Make changes
git add .
git commit -m "Update server configuration"
git push origin main
```

### What Happens Automatically

1. **GitHub Actions** (2-5 minutes):

   ```
   ✅ Tests pass
   ✅ Build Docker image (ARM64)
   ✅ Push to ghcr.io/and3rn3t/minecraft-server:latest
   ```

2. **Raspberry Pi** (within 1 hour):
   ```
   ✅ Timer triggers (or on next boot)
   ✅ Pulls latest image from registry
   ✅ Restarts container with new image
   ```

### Manual Trigger (Immediate Update)

If you want to update immediately without waiting:

```bash
# On Raspberry Pi
sudo systemctl start minecraft-update.service

# Or manually
cd ~/minecraft-server
docker compose pull
docker compose up -d --force-recreate
```

## Monitoring Updates

### Check Update Log

```bash
# View update service logs
sudo journalctl -u minecraft-update.service -f

# View update log file
tail -f /var/log/minecraft-update.log
```

### Check Current Image

```bash
# See what image is running
docker inspect minecraft-server | grep Image

# Compare with registry
docker pull ghcr.io/and3rn3t/minecraft-server:latest --dry-run
```

### Check for Updates

```bash
# See if local image is outdated
docker images ghcr.io/and3rn3t/minecraft-server:latest

# Pull to see if there's a newer version
docker compose pull
```

## Troubleshooting

### Image Pull Fails with 403

**Problem**: Authentication failed

**Solution**:

```bash
# Re-authenticate
echo "YOUR_TOKEN" | docker login ghcr.io -u and3rn3t --password-stdin

# Verify
docker pull ghcr.io/and3rn3t/minecraft-server:latest
```

### Container Doesn't Update

**Problem**: Service pulls but container doesn't restart

**Solution**:

```bash
# Force recreate
docker compose up -d --force-recreate

# Or restart service
sudo systemctl restart minecraft.service
```

### Registry Image Not Found

**Problem**: Image doesn't exist in registry

**Check**:

1. Verify CI workflow completed successfully
2. Check GitHub Actions logs
3. Verify image exists: `docker pull ghcr.io/and3rn3t/minecraft-server:latest`

### Timer Not Running

**Problem**: Auto-update timer not active

**Solution**:

```bash
# Check timer status
sudo systemctl status minecraft-update.timer

# Enable and start
sudo systemctl enable minecraft-update.timer
sudo systemctl start minecraft-update.timer

# List all timers
sudo systemctl list-timers
```

## Security Best Practices

1. **Use Personal Access Token** - Not your GitHub password
2. **Limit Token Scope** - Only `read:packages` permission
3. **Rotate Tokens** - Change periodically
4. **Use Private Registry** - If repository is private
5. **Monitor Access** - Check GitHub audit logs

## Advanced: Tag-Based Deployment

For production, use specific tags instead of `latest`:

```yaml
# In docker-compose.yml
image: ghcr.io/and3rn3t/minecraft-server:v1.4.0
```

Update the tag when you want to deploy a specific version.

## Summary

✅ **CI pushes images** on every main branch commit  
✅ **Pi pulls automatically** via systemd timer (every hour)  
✅ **Container restarts** with new image  
✅ **Zero manual intervention** needed

Your Raspberry Pi will now automatically stay up-to-date with the latest code!
