# Cloudflare DDNS Setup Guide for mine.andernet.dev

This guide will help you set up Cloudflare Dynamic DNS for `mine.andernet.dev`.

## Prerequisites

1. **Cloudflare Account**: You need a Cloudflare account with `andernet.dev` domain
2. **Domain in Cloudflare**: The domain `andernet.dev` must be managed by Cloudflare
3. **DNS Record**: We'll create or update an A record for `mine.andernet.dev`

## Step 1: Get Cloudflare API Token

1. **Log in to Cloudflare Dashboard**:

   - Visit: <https://dash.cloudflare.com/>
   - Sign in to your account

2. **Navigate to API Tokens**:

   - Click on your profile icon (top right)
   - Select "My Profile"
   - Go to "API Tokens" tab
   - Or directly visit: <https://dash.cloudflare.com/profile/api-tokens>

3. **Create a New Token**:

   - Click "Create Token"
   - Click "Get started" on "Edit zone DNS" template
   - **Zone Resources**: Select "Include" → "Specific zone" → `andernet.dev`
   - **Permissions**: Should be "Zone" → "DNS" → "Edit"
   - **Zone Resources**: Should show `andernet.dev`
   - Click "Continue to summary"
   - Review and click "Create Token"

4. **Copy the Token**:
   - **IMPORTANT**: Copy the token immediately - you won't be able to see it again!
   - Save it securely

## Step 2: Get Zone ID

1. **Go to Domain Overview**:

   - In Cloudflare dashboard, select `andernet.dev` domain
   - You'll be on the Overview page

2. **Find Zone ID**:
   - Scroll down to the right sidebar
   - Look for "Zone ID" section
   - Copy the Zone ID (it's a long alphanumeric string)

## Step 3: Create DNS Record (if needed)

1. **Check if Record Exists**:

   - Go to DNS → Records in Cloudflare dashboard
   - Look for `mine` A record

2. **Create Record if Missing**:
   - Click "Add record"
   - **Type**: A
   - **Name**: `mine` (or `mine.andernet.dev` - both work)
   - **IPv4 address**: `1.1.1.1` (temporary - will be updated automatically)
   - **Proxy status**: DNS only (gray cloud) or Proxied (orange cloud)
     - **DNS only** recommended for Minecraft server
   - **TTL**: Auto
   - Click "Save"

## Step 4: Configure DDNS Script

1. **Edit Configuration File**:

   ```bash
   nano config/ddns.conf
   ```

2. **Update the following values**:

   ```bash
   # Replace YOUR_API_TOKEN_HERE with your actual API token
   CLOUDFLARE_API_TOKEN=your-actual-token-here

   # Replace YOUR_ZONE_ID_HERE with your actual Zone ID
   CLOUDFLARE_ZONE_ID=your-actual-zone-id-here

   # Enable DDNS
   DDNS_ENABLED=true
   ```

3. **Set Secure Permissions**:

   ```bash
   chmod 600 config/ddns.conf
   ```

## Step 5: Test Configuration

1. **Check Status**:

   ```bash
   ./scripts/ddns-updater.sh status
   ```

2. **Test Update**:

   ```bash
   ./scripts/ddns-updater.sh update
   ```

3. **Verify in Cloudflare**:
   - Go to DNS → Records
   - Check that `mine.andernet.dev` A record shows your current public IP
   - You can get your public IP with: `curl https://api.ipify.org`

## Step 6: Set Up Automatic Updates

### Option A: Cron (Recommended)

```bash
# Edit crontab
crontab -e

# Add this line to update every 5 minutes
*/5 * * * * /path/to/minecraft/scripts/ddns-updater.sh update >> /path/to/minecraft/logs/ddns-updater.log 2>&1
```

### Option B: Systemd Timer

Create service file:

```bash
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

Create timer file:

```bash
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

Enable and start:

```bash
sudo systemctl enable minecraft-ddns.timer
sudo systemctl start minecraft-ddns.timer
```

## Verification

1. **Check DNS Record**:

   ```bash
   nslookup mine.andernet.dev
   # or
   dig +short mine.andernet.dev
   ```

2. **Check Logs**:

   ```bash
   tail -f logs/ddns-updater.log
   ```

3. **Test Connection**:

   - Once DNS propagates (can take a few minutes), test:

   ```bash
   ping mine.andernet.dev
   ```

## Troubleshooting

### "DNS record not found" Error

**Solution**: Make sure the A record exists in Cloudflare:

1. Go to DNS → Records
2. Create `mine` A record if it doesn't exist
3. The record name should be exactly `mine.andernet.dev` or just `mine`

### "Invalid API token" Error

**Solution**:

1. Verify token has "Zone.DNS Edit" permission
2. Verify token is for `andernet.dev` zone
3. Create a new token if needed

### "Wrong Zone ID" Error

**Solution**:

1. Go to Cloudflare dashboard → `andernet.dev` → Overview
2. Copy Zone ID from right sidebar
3. Make sure it matches exactly (no extra spaces)

### Updates Not Working

**Check**:

1. `DDNS_ENABLED=true` in config
2. Script is executable: `chmod +x scripts/ddns-updater.sh`
3. Check logs: `tail -f logs/ddns-updater.log`
4. Test manually: `./scripts/ddns-updater.sh update`

## Security Notes

1. **Protect API Token**:

   - Never commit `ddns.conf` to git
   - Keep file permissions at 600: `chmod 600 config/ddns.conf`
   - Use API tokens (not Global API Key) for better security

2. **Token Permissions**:

   - Use minimum required permissions (Zone.DNS Edit only)
   - Token should be scoped to specific zone (`andernet.dev`)

3. **Monitor Logs**:
   - Regularly check `logs/ddns-updater.log`
   - Watch for failed updates or errors

## Using the Domain

Once configured, players can connect using:

```
mine.andernet.dev:25565
```

Or if using default port:

```
mine.andernet.dev
```

## Next Steps

1. **Test the setup** with manual update
2. **Set up automatic updates** (cron or systemd)
3. **Monitor logs** for the first few updates
4. **Update server.properties** if needed to reflect the domain

## See Also

- [Dynamic DNS Guide](DYNAMIC_DNS.md) - Complete DDNS documentation
- [Troubleshooting Guide](TROUBLESHOOTING.md) - Common issues and solutions
