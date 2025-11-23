# Dynamic DNS (DDNS) Integration Guide

This guide covers the Dynamic DNS integration for automatically updating your DNS records when your public IP address changes.

## Overview

The Dynamic DNS system supports three providers:

- **DuckDNS** - Free, simple DDNS service
- **No-IP** - Popular DDNS service with free tier
- **Cloudflare DNS** - Professional DNS management with API

## Quick Start

### 1. Choose a Provider

**DuckDNS** (Recommended for beginners):

- Free service
- Simple setup
- No email verification required
- Get started at: <https://www.duckdns.org/>

**No-IP**:

- Free tier available
- More features than DuckDNS
- Requires email verification
- Get started at: <https://www.noip.com/>

**Cloudflare DNS**:

- Professional DNS management
- Requires existing domain
- More configuration options
- Get started at: <https://dash.cloudflare.com/>

### 2. Configure DDNS

1. **Create configuration file:**

   ```bash
   cp config/ddns.conf.example config/ddns.conf
   chmod 600 config/ddns.conf
   ```

2. **Edit configuration:**

   ```bash
   nano config/ddns.conf
   ```

3. **Set your provider and credentials** (see provider-specific sections below)

4. **Enable DDNS:**

   ```bash
   # In ddns.conf
   DDNS_ENABLED=true
   ```

### 3. Test Configuration

```bash
# Check status
./scripts/ddns-updater.sh status

# Test update once
./scripts/ddns-updater.sh update
```

### 4. Run Automatically

**Option A: Cron (Recommended)**

```bash
# Edit crontab
crontab -e

# Add line to update every 5 minutes
*/5 * * * * /path/to/minecraft/scripts/ddns-updater.sh update >> /path/to/minecraft/logs/ddns-updater.log 2>&1
```

**Option B: Systemd Timer**

```bash
# Create systemd service file
sudo nano /etc/systemd/system/minecraft-ddns.service
```

```ini
[Unit]
Description=Minecraft Server DDNS Updater
After=network.target

[Service]
Type=oneshot
ExecStart=/path/to/minecraft/scripts/ddns-updater.sh update
User=pi
WorkingDirectory=/path/to/minecraft

[Install]
WantedBy=multi-user.target
```

```bash
# Create timer file
sudo nano /etc/systemd/system/minecraft-ddns.timer
```

```ini
[Unit]
Description=Run DDNS updater every 5 minutes
Requires=minecraft-ddns.service

[Timer]
OnBootSec=1min
OnUnitActiveSec=5min

[Install]
WantedBy=timers.target
```

```bash
# Enable and start timer
sudo systemctl enable minecraft-ddns.timer
sudo systemctl start minecraft-ddns.timer
```

**Option C: Daemon Mode**

```bash
# Run as background daemon
nohup ./scripts/ddns-updater.sh daemon > /dev/null 2>&1 &
```

## Provider-Specific Configuration

### DuckDNS

1. **Get your token:**

   - Visit <https://www.duckdns.org/>
   - Sign in with GitHub, Google, or create account
   - Go to your domains page
   - Copy your token

2. **Configure:**

   ```bash
   # In config/ddns.conf
   DDNS_PROVIDER=duckdns
   DUCKDNS_TOKEN=your-token-here
   DUCKDNS_DOMAIN=yourdomain.duckdns.org
   DDNS_ENABLED=true
   ```

3. **Test:**

   ```bash
   ./scripts/ddns-updater.sh update
   ```

### No-IP

1. **Create account:**

   - Visit <https://www.noip.com/>
   - Create free account
   - Verify email address
   - Create a hostname (e.g., `minecraft.ddns.net`)

2. **Configure:**

   ```bash
   # In config/ddns.conf
   DDNS_PROVIDER=noip
   NOIP_USERNAME=your-username
   NOIP_PASSWORD=your-password
   NOIP_DOMAIN=yourdomain.ddns.net
   # Optional: specific hostname
   NOIP_HOSTNAME=subdomain.yourdomain.ddns.net
   DDNS_ENABLED=true
   ```

3. **Test:**

   ```bash
   ./scripts/ddns-updater.sh update
   ```

### Cloudflare DNS

1. **Get API token:**

   - Visit <https://dash.cloudflare.com/profile/api-tokens>
   - Click "Create Token"
   - Use "Edit zone DNS" template
   - Select your zone
   - Copy the token

2. **Get Zone ID:**

   - Go to your domain's overview page in Cloudflare
   - Copy the Zone ID from the right sidebar

3. **Configure:**

   ```bash
   # In config/ddns.conf
   DDNS_PROVIDER=cloudflare
   CLOUDFLARE_API_TOKEN=your-api-token-here
   CLOUDFLARE_ZONE_ID=your-zone-id-here
   CLOUDFLARE_DOMAIN=yourdomain.com
   # Optional: specific record name
   CLOUDFLARE_RECORD_NAME=subdomain.yourdomain.com
   DDNS_ENABLED=true
   ```

4. **Test:**

   ```bash
   ./scripts/ddns-updater.sh update
   ```

## Configuration Options

### Basic Settings

```bash
# Provider selection
DDNS_PROVIDER=duckdns  # Options: duckdns, noip, cloudflare

# Enable/disable DDNS
DDNS_ENABLED=true

# Update interval (minutes)
DDNS_UPDATE_INTERVAL=5
```

### Advanced Settings

```bash
# IP check service URL
DDNS_IP_CHECK_URL=https://api.ipify.org

# Verify SSL certificates
DDNS_VERIFY_SSL=true
```

## API Endpoints

### Get DDNS Status

**Endpoint:** `GET /api/ddns/status`

**Permission Required:** `settings.view`

**Response:**

```json
{
  "success": true,
  "status": "Provider: duckdns\nEnabled: true\n..."
}
```

### Update DDNS

**Endpoint:** `POST /api/ddns/update`

**Permission Required:** `settings.edit`

**Response:**

```json
{
  "success": true,
  "message": "DDNS updated successfully",
  "output": "..."
}
```

### Get DDNS Configuration

**Endpoint:** `GET /api/ddns/config`

**Permission Required:** `config.view`

**Response:**

```json
{
  "content": "# DDNS Configuration\n...",
  "is_example": false
}
```

### Save DDNS Configuration

**Endpoint:** `POST /api/ddns/config`

**Permission Required:** `config.edit`

**Request Body:**

```json
{
  "content": "# DDNS Configuration\nDDNS_PROVIDER=duckdns\n..."
}
```

**Response:**

```json
{
  "success": true,
  "message": "DDNS configuration saved successfully",
  "backup": "config/ddns.conf.backup.20250127_120000"
}
```

## Command Line Usage

### Update Once

```bash
./scripts/ddns-updater.sh update
```

### Run as Daemon

```bash
./scripts/ddns-updater.sh daemon
```

### Show Status

```bash
./scripts/ddns-updater.sh status
```

### Create Config

```bash
./scripts/ddns-updater.sh config
```

## Troubleshooting

### "Failed to get public IP address"

**Causes:**

- No internet connection
- Firewall blocking curl
- IP check service down

**Solutions:**

1. Check internet connectivity: `ping -c 3 8.8.8.8`
2. Try alternative IP check URL in config
3. Check firewall rules

### "DuckDNS update failed"

**Causes:**

- Invalid token
- Invalid domain
- Network issues

**Solutions:**

1. Verify token at <https://www.duckdns.org/>
2. Check domain spelling
3. Test manually: `curl "https://www.duckdns.org/update?domains=YOURDOMAIN&token=YOURTOKEN&ip=YOURIP"`

### "No-IP update failed"

**Causes:**

- Invalid credentials
- Hostname not found
- Account not verified

**Solutions:**

1. Verify username/password
2. Check hostname exists in No-IP dashboard
3. Verify email address

### "Cloudflare DNS update failed"

**Causes:**

- Invalid API token
- Wrong Zone ID
- DNS record not found
- Insufficient permissions

**Solutions:**

1. Verify API token has "Zone.DNS Edit" permission
2. Check Zone ID matches your domain
3. Ensure DNS record exists (create A record if needed)
4. Verify record name matches exactly

### Updates Not Happening Automatically

**Causes:**

- Cron/systemd not configured
- Script not executable
- DDNS_ENABLED=false

**Solutions:**

1. Check cron/systemd status
2. Make script executable: `chmod +x scripts/ddns-updater.sh`
3. Verify `DDNS_ENABLED=true` in config
4. Check logs: `tail -f logs/ddns-updater.log`

## Security Best Practices

1. **File Permissions:**

   ```bash
   chmod 600 config/ddns.conf
   ```

   Restrict access to configuration file containing credentials.

2. **API Tokens:**

   - Use API tokens instead of global API keys when possible
   - Rotate tokens periodically
   - Use minimum required permissions

3. **Logging:**

   - Review logs regularly: `tail -f logs/ddns-updater.log`
   - Monitor for failed updates
   - Check for suspicious activity

4. **Network Security:**
   - Use HTTPS for API calls (DDNS_VERIFY_SSL=true)
   - Consider VPN for additional security
   - Monitor DNS record changes

## Examples

### DuckDNS Setup

```bash
# 1. Get token from duckdns.org
# 2. Create config
cat > config/ddns.conf << EOF
DDNS_PROVIDER=duckdns
DDNS_ENABLED=true
DUCKDNS_TOKEN=abc123-def456-ghi789
DUCKDNS_DOMAIN=myminecraft.duckdns.org
DDNS_UPDATE_INTERVAL=5
EOF

chmod 600 config/ddns.conf

# 3. Test
./scripts/ddns-updater.sh update

# 4. Add to cron
(crontab -l 2>/dev/null; echo "*/5 * * * * $(pwd)/scripts/ddns-updater.sh update >> $(pwd)/logs/ddns-updater.log 2>&1") | crontab -
```

### Cloudflare Setup

```bash
# 1. Get API token and Zone ID from Cloudflare
# 2. Create config
cat > config/ddns.conf << EOF
DDNS_PROVIDER=cloudflare
DDNS_ENABLED=true
CLOUDFLARE_API_TOKEN=your-token-here
CLOUDFLARE_ZONE_ID=your-zone-id-here
CLOUDFLARE_DOMAIN=example.com
CLOUDFLARE_RECORD_NAME=minecraft.example.com
DDNS_UPDATE_INTERVAL=5
EOF

chmod 600 config/ddns.conf

# 3. Test
./scripts/ddns-updater.sh update

# 4. Set up systemd timer (see above)
```

## Integration with Minecraft Server

Once DDNS is configured, players can connect using your domain:

```
minecraft.yourdomain.duckdns.org:25565
```

Or if using default port:

```
minecraft.yourdomain.duckdns.org
```

## Monitoring

### Check Update Logs

```bash
tail -f logs/ddns-updater.log
```

### Verify DNS Record

```bash
# Check current DNS record
nslookup yourdomain.duckdns.org

# Or with dig
dig +short yourdomain.duckdns.org
```

### Check Current Public IP

```bash
curl https://api.ipify.org
```

## See Also

- [API Documentation](API.md) - REST API reference
- [Web Interface Guide](WEB_INTERFACE.md) - Web admin panel
- [Troubleshooting Guide](TROUBLESHOOTING.md) - Common issues
