# Cloud Backup Integration Guide

This guide covers cloud backup integration with multiple providers for off-site backup storage.

## Overview

Cloud backup provides:

- **Off-site storage** - Backups stored in the cloud
- **Disaster recovery** - Restore from cloud if local backups are lost
- **Cost-effective** - Multiple provider options
- **S3-compatible** - Standard S3 API support

## Supported Providers

The project supports three cloud backup providers:

1. **Cloudflare R2** (Recommended) - No egress fees, S3-compatible
2. **AWS S3** - Industry standard, multiple storage classes
3. **Backblaze B2** - Cost-effective, S3-compatible API

## Provider Comparison

| Feature          | Cloudflare R2 | AWS S3     | Backblaze B2     |
| ---------------- | ------------- | ---------- | ---------------- |
| Egress Fees      | **FREE**      | Paid       | Paid             |
| Storage Cost     | $0.015/GB     | $0.023/GB  | $0.005/GB        |
| S3-Compatible    | ✅ Yes        | ✅ Native  | ✅ Yes           |
| Setup Complexity | Easy          | Medium     | Easy             |
| Best For         | Raspberry Pi  | Enterprise | Budget-conscious |

## Cloudflare R2 Setup (Recommended)

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

### Cloudflare R2

```bash
# Upload backup
./scripts/cloud-backup-r2.sh upload backups/minecraft_backup_20250127.tar.gz

# List backups
./scripts/cloud-backup-r2.sh list

# Download backup
./scripts/cloud-backup-r2.sh download minecraft_backup_20250127.tar.gz

# Sync all backups
./scripts/cloud-backup-r2.sh sync

# Test connection
./scripts/cloud-backup-r2.sh test
```

### AWS S3

```bash
# Upload backup
./scripts/cloud-backup-s3.sh upload backups/minecraft_backup_20250127.tar.gz

# List backups
./scripts/cloud-backup-s3.sh list

# Download backup
./scripts/cloud-backup-s3.sh download minecraft_backup_20250127.tar.gz

# Sync all backups
./scripts/cloud-backup-s3.sh sync

# Test connection
./scripts/cloud-backup-s3.sh test
```

### Backblaze B2

```bash
# Upload backup
./scripts/cloud-backup-b2.sh upload backups/minecraft_backup_20250127.tar.gz

# List backups
./scripts/cloud-backup-b2.sh list

# Download backup
./scripts/cloud-backup-b2.sh download minecraft_backup_20250127.tar.gz

# Sync all backups
./scripts/cloud-backup-b2.sh sync

# Test connection
./scripts/cloud-backup-b2.sh test
```

## Automated Cloud Backup

### Integration with Backup Scheduler

To automatically upload backups to cloud after creation:

1. **Choose provider** and edit corresponding config:

   - `config/cloud-backup-r2.conf` for Cloudflare R2
   - `config/cloud-backup-s3.conf` for AWS S3
   - `config/cloud-backup-b2.conf` for Backblaze B2

2. **Enable auto-upload**:

   ```bash
   AUTO_UPLOAD="true"
   ```

3. **Modify backup script** to call cloud upload after backup creation.

### Manual Integration

Add to your backup script:

```bash
# After creating backup
BACKUP_FILE="backups/minecraft_backup_20250127.tar.gz"

# Try R2 first (recommended)
if [ -f "config/cloud-backup-r2.conf" ]; then
    source config/cloud-backup-r2.conf
    if [ "$AUTO_UPLOAD" = "true" ]; then
        ./scripts/cloud-backup-r2.sh upload "$BACKUP_FILE"
    fi
fi

# Or use S3
if [ -f "config/cloud-backup-s3.conf" ]; then
    source config/cloud-backup-s3.conf
    if [ "$AUTO_UPLOAD" = "true" ]; then
        ./scripts/cloud-backup-s3.sh upload "$BACKUP_FILE"
    fi
fi

# Or use B2
if [ -f "config/cloud-backup-b2.conf" ]; then
    source config/cloud-backup-b2.conf
    if [ "$AUTO_UPLOAD" = "true" ]; then
        ./scripts/cloud-backup-b2.sh upload "$BACKUP_FILE"
    fi
fi
```

## Restore from Cloud

### Full Restore Process

1. **Download backup from cloud** (choose your provider):

   ```bash
   # From R2
   ./scripts/cloud-backup-r2.sh download minecraft_backup_20250127.tar.gz

   # From S3
   ./scripts/cloud-backup-s3.sh download minecraft_backup_20250127.tar.gz

   # From B2
   ./scripts/cloud-backup-b2.sh download minecraft_backup_20250127.tar.gz
   ```

2. **Stop server**:

   ```bash
   ./manage.sh stop
   ```

3. **Restore backup**:

   ```bash
   # Extract backup
   tar -xzf backups/minecraft_backup_20250127.tar.gz -C ./data/
   ```

4. **Start server**:

   ```bash
   ./manage.sh start
   ```

## Cost Considerations

### Provider Pricing Comparison

**Cloudflare R2:**

- Storage: $0.015/GB/month
- Operations: $4.50 per million writes, $0.36 per million reads
- **Egress: FREE** (no egress fees!)

**AWS S3:**

- Storage: $0.023/GB/month (STANDARD)
- Operations: $0.005 per 1,000 requests
- Egress: $0.09/GB (first 10TB)

**Backblaze B2:**

- Storage: $0.005/GB/month
- Operations: Free (first 2,500 class C operations/day)
- Egress: $0.01/GB

### Cost Example

For a typical Minecraft server (500 MB backups, 30 backups/month):

| Provider | Storage Cost | Egress Cost\* | Total/Month |
| -------- | ------------ | ------------- | ----------- |
| **R2**   | $0.23        | **$0.00**     | **$0.23**   |
| **B2**   | $0.08        | $0.15         | $0.23       |
| **S3**   | $0.35        | $0.45         | $0.80       |

\*Assuming 1 restore per month (500 MB download)

**Recommendation**: Cloudflare R2 for Raspberry Pi users due to no egress fees!

## Security Best Practices

1. **Never commit credentials** - Keep all `cloud-backup-*.conf` files in `.gitignore`
2. **Use least privilege** - Create API tokens/keys with only necessary permissions
3. **Rotate keys** - Regularly rotate API tokens and access keys
4. **Encrypt backups** - Consider encrypting backups before upload
5. **Monitor usage** - Check provider dashboards for unusual activity
6. **Use IAM roles** (AWS) - Prefer IAM roles over access keys when possible
7. **Enable MFA** - Use multi-factor authentication for provider accounts

## Troubleshooting

### Upload Fails

**Issue**: Upload fails with authentication error

**Solutions**:

- Verify credentials in config file
- Check API token/access key permissions
- Test connection: `./scripts/cloud-backup-{provider}.sh test`
- Verify bucket exists and is accessible
- Check network connectivity

### Download Fails

**Issue**: Download fails or file not found

**Solutions**:

- Verify backup name (use `list` command to see available backups)
- Check bucket name and prefix
- Verify endpoint URL (for R2)
- Check region (for S3)
- Verify file permissions

### CLI Tools Not Found

**Issue**: Script fails because CLI tool not installed

**Solutions**:

**AWS CLI** (for R2 and S3):

```bash
# Install AWS CLI
pip install awscli

# Or on Debian/Ubuntu
sudo apt-get install awscli
```

**B2 CLI** (for Backblaze B2):

```bash
# Install B2 SDK
pip install b2sdk

# Or install B2 command-line tool
# See: https://www.backblaze.com/b2/docs/quick_command_line.html
```

### High Costs (S3/B2)

**Issue**: Unexpected high costs from cloud provider

**Solutions**:

- Check egress/bandwidth usage
- Consider switching to Cloudflare R2 (no egress fees)
- Use appropriate storage class (S3 STANDARD_IA for infrequent access)
- Enable lifecycle policies to delete old backups
- Monitor usage in provider dashboard

## AWS S3 Setup

### 1. Create S3 Bucket

1. Log in to [AWS Console](https://console.aws.amazon.com/)
2. Navigate to **S3** > **Create bucket**
3. Enter bucket name (must be globally unique)
4. Choose region (closest to you)
5. Configure settings (versioning, encryption, etc.)
6. Click **Create bucket**

### 2. Create IAM User and Access Keys

1. Go to **IAM** > **Users** > **Create user**
2. Set username (e.g., `minecraft-backup-user`)
3. Attach policy: `AmazonS3FullAccess` (or custom policy for specific bucket)
4. Go to **Security credentials** tab
5. Click **Create access key**
6. Copy **Access Key ID** and **Secret Access Key**

### 3. Configure Backup Script

1. Copy example config:

   ```bash
   cp config/cloud-backup-s3.conf.example config/cloud-backup-s3.conf
   ```

2. Edit `config/cloud-backup-s3.conf`:
   ```bash
   AWS_ACCESS_KEY_ID="your-access-key-id"
   AWS_SECRET_ACCESS_KEY="your-secret-access-key"
   AWS_REGION="us-east-1"
   S3_BUCKET_NAME="minecraft-backups"
   S3_PREFIX="minecraft-backups"
   S3_STORAGE_CLASS="STANDARD"
   ```

### 4. Usage

```bash
# Upload backup
./scripts/cloud-backup-s3.sh upload backups/minecraft_backup_20250127.tar.gz

# List backups
./scripts/cloud-backup-s3.sh list

# Download backup
./scripts/cloud-backup-s3.sh download minecraft_backup_20250127.tar.gz

# Test connection
./scripts/cloud-backup-s3.sh test
```

### S3 Storage Classes

Choose based on access patterns:

- **STANDARD** - Frequent access (default)
- **STANDARD_IA** - Infrequent access (cheaper storage)
- **GLACIER** - Archive storage (very cheap, slow retrieval)
- **DEEP_ARCHIVE** - Long-term archive (cheapest, slowest)

## Backblaze B2 Setup

### 1. Create B2 Bucket

1. Log in to [Backblaze B2](https://www.backblaze.com/b2/cloud-storage.html)
2. Go to **Buckets** > **Create a Bucket**
3. Enter bucket name
4. Choose bucket type (Private recommended)
5. Click **Create a Bucket**

### 2. Create Application Key

1. Go to **App Keys** > **Add a New Application Key**
2. Set key name (e.g., `minecraft-backup-key`)
3. Select bucket access (or all buckets)
4. Grant permissions:
   - List Files
   - Read Files
   - Write Files
   - Delete Files
5. Click **Create New Key**
6. Copy **keyID** and **applicationKey**

### 3. Install B2 CLI

```bash
# Install B2 SDK
pip install b2sdk

# Or install B2 command-line tool
# See: https://www.backblaze.com/b2/docs/quick_command_line.html
```

### 4. Configure Backup Script

1. Copy example config:

   ```bash
   cp config/cloud-backup-b2.conf.example config/cloud-backup-b2.conf
   ```

2. Edit `config/cloud-backup-b2.conf`:
   ```bash
   B2_KEY_ID="your-key-id"
   B2_APPLICATION_KEY="your-application-key"
   B2_BUCKET_NAME="minecraft-backups"
   B2_PREFIX="minecraft-backups"
   ```

### 5. Usage

```bash
# Upload backup
./scripts/cloud-backup-b2.sh upload backups/minecraft_backup_20250127.tar.gz

# List backups
./scripts/cloud-backup-b2.sh list

# Download backup
./scripts/cloud-backup-b2.sh download minecraft_backup_20250127.tar.gz

# Test connection
./scripts/cloud-backup-b2.sh test
```

## Choosing a Provider

### Cloudflare R2 (Best for Raspberry Pi)

**Pros:**

- No egress fees (huge savings!)
- S3-compatible API
- Easy setup
- Good performance

**Cons:**

- Newer service (less mature)
- Limited regions

**Best for:** Raspberry Pi users, frequent restores

### AWS S3 (Best for Enterprise)

**Pros:**

- Industry standard
- Multiple storage classes
- Global infrastructure
- Advanced features

**Cons:**

- Egress fees can be expensive
- More complex pricing
- Requires AWS account

**Best for:** Enterprise deployments, AWS ecosystem users

### Backblaze B2 (Best for Budget)

**Pros:**

- Lowest storage cost ($0.005/GB)
- S3-compatible API
- Simple pricing
- Good performance

**Cons:**

- Egress fees (but lower than AWS)
- Smaller ecosystem

**Best for:** Budget-conscious users, long-term storage

## Unified Cloud Backup Script

For convenience, you can create a unified script that supports all providers:

```bash
# Example unified script usage
./scripts/cloud-backup.sh r2 upload backup.tar.gz
./scripts/cloud-backup.sh s3 upload backup.tar.gz
./scripts/cloud-backup.sh b2 upload backup.tar.gz
```

## Resources

- [Cloudflare R2 Documentation](https://developers.cloudflare.com/r2/)
- [R2 Pricing](https://developers.cloudflare.com/r2/pricing/)
- [AWS S3 Documentation](https://docs.aws.amazon.com/s3/)
- [AWS S3 Pricing](https://aws.amazon.com/s3/pricing/)
- [Backblaze B2 Documentation](https://www.backblaze.com/b2/docs/)
- [B2 Pricing](https://www.backblaze.com/b2/pricing.html)
- [AWS CLI Documentation](https://aws.amazon.com/cli/)
- [B2 CLI Documentation](https://www.backblaze.com/b2/docs/quick_command_line.html)

## See Also

- [Backup & Monitoring Guide](BACKUP_AND_MONITORING.md) - Local backup management
- [Installation Guide](INSTALL.md) - Server setup
