# How to Update the Codebase on Raspberry Pi 5

This guide shows you how to pull the latest code changes from GitHub and update all components on your Raspberry Pi 5.

## Quick Update

### Simple Git Pull

```bash
cd ~/minecraft-server
git pull
```

### Complete Update (Recommended)

```bash
cd ~/minecraft-server
git pull
./scripts/update-codebase.sh
```

## Step-by-Step Update Process

### Step 1: Navigate to Project Directory

```bash
cd ~/minecraft-server
# Or wherever you cloned the repository
```

### Step 2: Check Current Status

```bash
# See what branch you're on
git branch

# See current commit
git log -1 --oneline

# Check for uncommitted changes
git status
```

### Step 3: Stash Local Changes (if needed)

If you have local modifications you want to keep:

```bash
# Save your changes
git stash

# Pull updates
git pull

# Reapply your changes (if needed)
git stash pop
```

### Step 4: Pull Latest Changes

```bash
# Pull from main branch
git pull origin main

# Or if you're on a different branch
git pull origin <branch-name>
```

### Step 5: Update Components

After pulling code, update the components that changed:

#### Update Web Interface (if web/ changed)

```bash
cd ~/minecraft-server/web
npm install  # Install new dependencies
npm run build  # Rebuild for production
sudo systemctl reload nginx  # Reload web server
```

#### Update API Server (if api/ changed)

```bash
cd ~/minecraft-server/api
pip3 install --user -r requirements.txt  # Install new dependencies
sudo systemctl restart minecraft-api.service  # Restart API
```

#### Update Docker Image (if Dockerfile or docker-compose.yml changed)

```bash
cd ~/minecraft-server
docker compose pull  # Pull latest image
docker compose up -d --force-recreate  # Recreate container
```

#### Update Systemd Services (if systemd/ changed)

```bash
cd ~/minecraft-server
sudo cp systemd/*.service /etc/systemd/system/
sudo systemctl daemon-reload
```

## Automated Update Script

Use the provided script for a complete update:

```bash
cd ~/minecraft-server
./scripts/update-codebase.sh
```

This script will:

1. Check git status
2. Pull latest changes
3. Update dependencies (npm, pip)
4. Rebuild web interface if needed
5. Restart services if needed

## Handling Conflicts

### If Git Pull Fails with Conflicts

```bash
# See what files have conflicts
git status

# Option 1: Keep your local changes
git checkout --ours <file>

# Option 2: Use remote changes
git checkout --theirs <file>

# Option 3: Manually resolve conflicts
nano <file>  # Edit and resolve conflicts

# After resolving, mark as resolved
git add <file>
git commit -m "Resolve merge conflicts"
```

### If You Want to Discard All Local Changes

```bash
# WARNING: This will lose all local changes!
git reset --hard origin/main
git clean -fd  # Remove untracked files
```

## Update Specific Components

### Update Only Web Interface

```bash
cd ~/minecraft-server
git pull
cd web
npm install
npm run build
sudo systemctl reload nginx
```

### Update Only API Server

```bash
cd ~/minecraft-server
git pull
cd api
pip3 install --user -r requirements.txt
sudo systemctl restart minecraft-api.service
```

### Update Only Docker Configuration

```bash
cd ~/minecraft-server
git pull
docker compose pull
docker compose up -d --force-recreate
```

## Automatic Updates (Optional)

### Set Up Cron Job for Daily Updates

```bash
# Edit crontab
crontab -e

# Add this line to update codebase daily at 3 AM
0 3 * * * cd ~/minecraft-server && git pull && ./scripts/update-codebase.sh >> /var/log/codebase-update.log 2>&1
```

### Set Up Systemd Timer for Updates

Create `/etc/systemd/system/minecraft-codebase-update.service`:

```ini
[Unit]
Description=Update Minecraft Server Codebase
After=network-online.target

[Service]
Type=oneshot
WorkingDirectory=/home/pi/minecraft-server
ExecStart=/bin/sh -c 'git pull && ./scripts/update-codebase.sh'
User=pi
Group=pi
```

Create `/etc/systemd/system/minecraft-codebase-update.timer`:

```ini
[Unit]
Description=Update Codebase Daily
Requires=minecraft-codebase-update.service

[Timer]
OnCalendar=daily
Persistent=true

[Install]
WantedBy=timers.target
```

Enable the timer:

```bash
sudo systemctl daemon-reload
sudo systemctl enable minecraft-codebase-update.timer
sudo systemctl start minecraft-codebase-update.timer
```

## Verification

After updating, verify everything is working:

```bash
# Check all services
./scripts/check-services.sh

# Check git status
git status

# Check web interface
curl http://localhost/

# Check API
curl http://localhost:8080/api/status

# Check Minecraft server
docker ps | grep minecraft-server
```

## Troubleshooting

### Git Pull Fails: "Permission Denied"

```bash
# Check repository permissions
ls -la ~/minecraft-server

# Fix ownership if needed
sudo chown -R pi:pi ~/minecraft-server
```

### Git Pull Fails: "Not a Git Repository"

```bash
# If you copied files instead of cloning
cd ~/minecraft-server
git init
git remote add origin https://github.com/and3rn3t/minecraft.git
git fetch
git checkout -b main origin/main
```

### Dependencies Fail to Install

```bash
# For npm
cd ~/minecraft-server/web
rm -rf node_modules package-lock.json
npm install

# For pip
cd ~/minecraft-server/api
pip3 install --user --upgrade pip
pip3 install --user -r requirements.txt
```

### Services Won't Restart

```bash
# Check service status
sudo systemctl status minecraft-api.service
sudo systemctl status minecraft-web.service

# Check logs
sudo journalctl -u minecraft-api.service -n 50
sudo journalctl -u minecraft-web.service -n 50

# Restart manually
sudo systemctl restart minecraft-api.service
sudo systemctl restart minecraft-web.service
```

## Best Practices

### 1. Always Backup Before Major Updates

```bash
# Backup server data
./scripts/manage.sh backup

# Backup configuration
cp docker-compose.yml docker-compose.yml.backup
cp -r config/ config.backup/
```

### 2. Test in Staging First (if possible)

```bash
# Clone to a test directory
cd ~
git clone https://github.com/and3rn3t/minecraft.git minecraft-test
cd minecraft-test
# Test changes here first
```

### 3. Update During Maintenance Window

Schedule updates when the server is not in use to avoid disrupting players.

### 4. Keep Track of Changes

```bash
# See what changed
git log --oneline -10

# See what files changed
git diff HEAD~1 HEAD --name-only
```

## Quick Reference

```bash
# Basic update
cd ~/minecraft-server && git pull

# Complete update
cd ~/minecraft-server && git pull && ./scripts/update-codebase.sh

# Update web only
cd ~/minecraft-server/web && git pull && npm install && npm run build

# Update API only
cd ~/minecraft-server/api && git pull && pip3 install --user -r requirements.txt

# Update Docker only
cd ~/minecraft-server && docker compose pull && docker compose up -d

# Check what changed
cd ~/minecraft-server && git log --oneline -5

# See uncommitted changes
cd ~/minecraft-server && git status
```

## Summary

**To update your codebase:**

1. ✅ Navigate to project directory: `cd ~/minecraft-server`
2. ✅ Pull latest changes: `git pull`
3. ✅ Update dependencies: `npm install` (web) or `pip3 install` (api)
4. ✅ Rebuild if needed: `npm run build` (web)
5. ✅ Restart services: `sudo systemctl restart <service>`

For automated updates, use the `update-codebase.sh` script or set up a cron job/systemd timer.
