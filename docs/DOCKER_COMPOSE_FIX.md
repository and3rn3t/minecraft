# Quick Fix: Docker Compose Installation Conflict

## Prerequisites: Install Docker First

**If you see `docker: command not found`**, you need to install Docker first:

```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
rm get-docker.sh

# IMPORTANT: Log out and back in for Docker permissions
exit
# Then SSH back in: ssh pi@docker-server.local

# Verify Docker is installed
docker --version
docker compose version
```

After installing Docker, the `docker-compose-plugin` is automatically included, so you don't need to install `docker-compose` separately.

---

## The Problem

You're getting this error when trying to install `docker-compose`:

```
dpkg: error processing archive ... trying to overwrite '/usr/libexec/docker/cli-plugins/docker-compose',
which is also in package docker-compose-plugin
```

## The Solution

The `docker-compose-plugin` is already installed with your Docker installation. You don't need the standalone `docker-compose` package.

### Quick Fix (Run These Commands)

```bash
# 1. Clean up the broken package state
sudo apt-get remove --purge docker-compose
sudo apt-get autoremove
sudo apt-get autoclean

# 2. Verify docker compose plugin works
docker compose version

# You should see something like:
# Docker Compose version v2.40.3
```

### Use Docker Compose Plugin

Instead of `docker-compose` (with hyphen), use `docker compose` (with space):

```bash
# Old way (standalone):
docker-compose up -d

# New way (plugin):
docker compose up -d
```

### All Docker Compose Commands

Replace all instances of `docker-compose` with `docker compose`:

| Old Command              | New Command              |
| ------------------------ | ------------------------ |
| `docker-compose up`      | `docker compose up`      |
| `docker-compose down`    | `docker compose down`    |
| `docker-compose pull`    | `docker compose pull`    |
| `docker-compose build`   | `docker compose build`   |
| `docker-compose logs`    | `docker compose logs`    |
| `docker-compose ps`      | `docker compose ps`      |
| `docker-compose restart` | `docker compose restart` |

### Update Systemd Services

If you have any systemd service files using `docker-compose`, update them:

```bash
# Edit the service file
sudo nano /etc/systemd/system/your-service.service

# Change:
ExecStart=/usr/bin/docker-compose up -d

# To:
ExecStart=/usr/bin/docker compose up -d
```

Then reload systemd:

```bash
sudo systemctl daemon-reload
sudo systemctl restart your-service.service
```

## Why This Happens

Modern Docker installations (Docker Engine 20.10+) include Docker Compose as a plugin. The plugin is installed as part of the Docker package and provides the same functionality as the standalone `docker-compose` package, but integrated directly into Docker.

The plugin approach is:

- ✅ More integrated with Docker
- ✅ Automatically updated with Docker
- ✅ Better performance
- ✅ Recommended by Docker

## Verification

After fixing, verify everything works:

```bash
# Check Docker Compose version
docker compose version

# Test with a simple command
docker compose --help

# If you have a docker-compose.yml, test it
docker compose config
```

## Still Having Issues?

If `docker compose version` doesn't work, the plugin might not be installed:

```bash
# Install the plugin
sudo apt-get update
sudo apt-get install -y docker-compose-plugin

# Verify
docker compose version
```

## Summary

1. ✅ Remove broken `docker-compose` package
2. ✅ Use `docker compose` (with space) instead of `docker-compose` (with hyphen)
3. ✅ Update any systemd services or scripts
4. ✅ You're all set!
