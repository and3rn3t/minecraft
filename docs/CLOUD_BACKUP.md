# Cloud Backup Integration Guide

This guide covers cloud backup integration with Cloudflare R2 (S3-compatible) for off-site backup storage.

## Overview

Cloud backup provides:

- **Off-site storage** - Backups stored in the cloud
- **Disaster recovery** - Restore from cloud if local backups are lost
- **Cost-effective** - Cloudflare R2 has no egress fees
- **S3-compatible** - Uses standard S3 API

## Cloudflare R2 Setup

### 1. Create R2 Bucket

1. Log in to [Cloudflare Dashboard](https://dash.cloudflare.com/)
2. Navigate to **R2** > **Create bucket**
3. Enter bucket name (e.g., `minecraft-backups`)
4. Choose location (closest to you)
5. Click **Create bucket**

### 2. Create API Token

1. In R2 dashboard, go to **Manage R2 API Tokens**
2. Click **Create API Token**
3. Set permissions:
   - **Object Read & Write** (for upload/download)
   - **Admin Read** (for listing)
4. Copy the **Access Key ID** and **Secret Access Key**

### 3. Get Account ID and Endpoint

1. In R2 dashboard, note your **Account ID** (32-character hex string)
2. Endpoint format: `https://<account-id>.r2.cloudflarestorage.com`

### 4. Configure Backup Script

1. Copy example config:

   ```bash
   cp config/cloud-backup-r2.conf.example config/cloud-backup-r2.conf
   ```

2. Edit `config/cloud-backup-r2.conf`:

   ```bash
   R2_ACCOUNT_ID="your-account-id"
   R2_ACCESS_KEY_ID="your-access-key-id"
   R2_SECRET_ACCESS_KEY="your-secret-access-key"
   R2_BUCKET_NAME="minecraft-backups"
   R2_ENDPOINT="https://your-account-id.r2.cloudflarestorage.com"
   R2_PREFIX="minecraft-backups"
   ```

3. **Important**: Add to `.gitignore`:

   ```bash
   config/cloud-backup-r2.conf
   ```

## Usage

### Upload Backup

```bash
# Upload a specific backup
./scripts/cloud-backup-r2.sh upload backups/minecraft_backup_20250127_120000.tar.gz

# Upload latest backup
./scripts/cloud-backup-r2.sh upload backups/$(ls -t backups/*.tar.gz | head -1)
```

### List Backups

```bash
# List all backups in R2
./scripts/cloud-backup-r2.sh list
```

### Download Backup

```bash
# Download backup from R2
./scripts/cloud-backup-r2.sh download minecraft_backup_20250127_120000.tar.gz

# Download to specific directory
./scripts/cloud-backup-r2.sh download minecraft_backup_20250127_120000.tar.gz /path/to/restore
```

### Sync All Backups

```bash
# Upload all local backups to R2
./scripts/cloud-backup-r2.sh sync
```

### Delete Backup

```bash
# Delete backup from R2
./scripts/cloud-backup-r2.sh delete minecraft_backup_20250127_120000.tar.gz
```

### Test Connection

```bash
# Test R2 connection and configuration
./scripts/cloud-backup-r2.sh test
```

## Automated Cloud Backup

### Integration with Backup Scheduler

To automatically upload backups to R2 after creation:

1. Edit `config/cloud-backup-r2.conf`:

   ```bash
   AUTO_UPLOAD="true"
   ```

2. Modify `scripts/backup-scheduler.sh` to call R2 upload after backup creation.

### Manual Integration

Add to your backup script:

```bash
# After creating backup
if [ -f "$BACKUP_FILE" ] && [ -f "config/cloud-backup-r2.conf" ]; then
    source config/cloud-backup-r2.conf
    if [ "$AUTO_UPLOAD" = "true" ]; then
        ./scripts/cloud-backup-r2.sh upload "$BACKUP_FILE"
    fi
fi
```

## Restore from Cloud

### Full Restore Process

1. **Download backup from R2**:

   ```bash
   ./scripts/cloud-backup-r2.sh download minecraft_backup_20250127_120000.tar.gz
   ```

2. **Stop server**:

   ```bash
   ./manage.sh stop
   ```

3. **Restore backup**:

   ```bash
   # Extract backup
   tar -xzf backups/minecraft_backup_20250127_120000.tar.gz -C ./data/
   ```

4. **Start server**:

   ```bash
   ./manage.sh start
   ```

## Cost Considerations

### Cloudflare R2 Pricing

- **Storage**: $0.015 per GB/month
- **Class A Operations** (writes): $4.50 per million
- **Class B Operations** (reads): $0.36 per million
- **Egress**: **FREE** (no egress fees!)

### Cost Example

For a typical Minecraft server:

- **Backup size**: 500 MB per backup
- **Backups per month**: 30 (daily)
- **Total storage**: ~15 GB
- **Monthly cost**: ~$0.23/month

Much cheaper than AWS S3 due to no egress fees!

## Security Best Practices

1. **Never commit credentials** - Keep `cloud-backup-r2.conf` in `.gitignore`
2. **Use least privilege** - Create API token with only necessary permissions
3. **Rotate keys** - Regularly rotate API tokens
4. **Encrypt backups** - Consider encrypting backups before upload
5. **Monitor usage** - Check R2 dashboard for unusual activity

## Troubleshooting

### Upload Fails

**Issue**: Upload fails with authentication error

**Solutions**:

- Verify credentials in config file
- Check API token permissions
- Test connection: `./scripts/cloud-backup-r2.sh test`

### Download Fails

**Issue**: Download fails or file not found

**Solutions**:

- Verify backup name (use `list` command to see available backups)
- Check bucket name and prefix
- Verify endpoint URL

### AWS CLI Not Found

**Issue**: Script fails because AWS CLI not installed

**Solutions**:

```bash
# Install AWS CLI
pip install awscli

# Or on Debian/Ubuntu
sudo apt-get install awscli
```

## Alternative: AWS S3

The script can be adapted for AWS S3:

1. Use AWS credentials instead of R2
2. Change endpoint to S3 endpoint
3. Note: S3 has egress fees (unlike R2)

## Resources

- [Cloudflare R2 Documentation](https://developers.cloudflare.com/r2/)
- [R2 Pricing](https://developers.cloudflare.com/r2/pricing/)
- [AWS CLI Documentation](https://aws.amazon.com/cli/)

## See Also

- [Backup & Monitoring Guide](BACKUP_AND_MONITORING.md) - Local backup management
- [Installation Guide](INSTALL.md) - Server setup
