# OAuth Setup Guide

This guide will help you configure OAuth authentication (Google and Apple) for your Minecraft server management system.

## Overview

OAuth allows users to sign in using their Google or Apple accounts instead of creating a separate username/password. This provides a more secure and convenient authentication method.

## Configuration File

OAuth settings are stored in `config/oauth.conf`. The file uses a simple key-value format:

```
APPLE_CLIENT_ID=your-value-here
APPLE_TEAM_ID=your-value-here
```

## Apple OAuth Setup

### Prerequisites

1. **Apple Developer Account** - You need a paid Apple Developer account ($99/year)
2. **Access to Apple Developer Portal** - https://developer.apple.com/account

### Step 1: Create a Services ID

1. Go to [Apple Developer Portal](https://developer.apple.com/account/resources/identifiers/list)
2. Click the **+** button to create a new identifier
3. Select **Services IDs** and click Continue
4. Fill in:
   - **Description**: Minecraft Server Management (or any name)
   - **Identifier**: `com.yourdomain.minecraft` (must be unique, reverse domain format)
5. Click Continue, then Register

### Step 2: Configure the Services ID

1. Click on your newly created Services ID
2. Check the box for **Sign in with Apple**
3. Click **Configure**
4. In the configuration:
   - **Primary App ID**: Select your app (or create one if needed)
   - **Website URLs**:
     - **Domains**: Add your domain (e.g., `localhost` for development, or your production domain)
     - **Return URLs**: Add your callback URL:
       - Development: `http://localhost:5173/oauth/callback`
       - Production: `https://yourdomain.com/oauth/callback`
5. Click **Save**, then **Continue**, then **Register**

### Step 3: Create a Key

1. Go to [Keys section](https://developer.apple.com/account/resources/authkeys/list)
2. Click the **+** button to create a new key
3. Fill in:
   - **Key Name**: Minecraft Server OAuth Key (or any name)
   - **Enable Sign in with Apple**: Check this box
4. Click **Configure** next to "Sign in with Apple"
5. Select your **Primary App ID** (the one you used in Step 2)
6. Click **Save**, then **Continue**, then **Register**
7. **IMPORTANT**: Download the key file (`.p8` file) - you can only download it once!
8. Note the **Key ID** shown on the page

### Step 4: Get Your Team ID

1. Go to [Membership section](https://developer.apple.com/account)
2. Your **Team ID** is displayed at the top (looks like: `ABC123DEF4`)

### Step 5: Configure oauth.conf

Edit `config/oauth.conf` and fill in the Apple OAuth values:

```conf
# Apple OAuth Configuration
APPLE_CLIENT_ID=com.yourdomain.minecraft
APPLE_TEAM_ID=ABC123DEF4
APPLE_KEY_ID=XYZ789ABC1
APPLE_PRIVATE_KEY=-----BEGIN PRIVATE KEY-----
MIGTAgEAMBMGByqGSM49AgEGCCqGSM49AwEHBHkwdwIBAQQg...
-----END PRIVATE KEY-----
APPLE_REDIRECT_URI=http://localhost:5173/oauth/callback
```

**Important Notes:**

1. **APPLE_CLIENT_ID**: This is the Services ID you created (e.g., `com.yourdomain.minecraft`)
2. **APPLE_TEAM_ID**: Your Apple Team ID (from Membership section)
3. **APPLE_KEY_ID**: The Key ID from the key you created
4. **APPLE_PRIVATE_KEY**: The entire contents of the `.p8` file you downloaded, including the `-----BEGIN PRIVATE KEY-----` and `-----END PRIVATE KEY-----` lines
5. **APPLE_REDIRECT_URI**:
   - For development: `http://localhost:5173/oauth/callback` (or whatever port your frontend runs on)
   - For production: `https://yourdomain.com/oauth/callback`

### Step 6: Format the Private Key

The private key from the `.p8` file should be formatted as a single line or multiple lines in the config file. You can either:

**Option A: Single line (recommended)**

```conf
APPLE_PRIVATE_KEY=-----BEGIN PRIVATE KEY-----\nMIGTAgEAMBMGByqGSM49AgEGCCqGSM49AwEHBHkwdwIBAQQg...\n-----END PRIVATE KEY-----
```

**Option B: Multi-line (if your config parser supports it)**

```conf
APPLE_PRIVATE_KEY=-----BEGIN PRIVATE KEY-----
MIGTAgEAMBMGByqGSM49AgEGCCqGSM49AwEHBHkwdwIBAQQg...
-----END PRIVATE KEY-----
```

### Step 7: Restart the API Server

After updating `config/oauth.conf`, restart your API server:

```bash
# If using Docker Compose
docker compose restart api

# If running directly
# Restart your Python API server
```

## Google OAuth Setup (Optional)

If you also want to enable Google OAuth:

### Step 1: Create OAuth Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
2. Create a new project or select an existing one
3. Click **Create Credentials** → **OAuth client ID**
4. If prompted, configure the OAuth consent screen first
5. Select **Web application**
6. Fill in:
   - **Name**: Minecraft Server Management
   - **Authorized redirect URIs**:
     - `http://localhost:5173/oauth/callback` (development)
     - `https://yourdomain.com/oauth/callback` (production)
7. Click **Create**
8. Copy the **Client ID** and **Client Secret**

### Step 2: Configure oauth.conf

```conf
# Google OAuth Configuration
GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-google-client-secret
GOOGLE_REDIRECT_URI=http://localhost:5173/oauth/callback
```

## Testing OAuth

1. **Start your servers**:

   ```bash
   # Start API server
   # Start web frontend
   ```

2. **Navigate to login page** in your browser

3. **Click "Sign in with Apple"** (or Google)

4. **Complete the OAuth flow**:

   - You'll be redirected to Apple/Google
   - Sign in with your account
   - Authorize the application
   - You'll be redirected back

5. **Verify**: You should be logged in and redirected to the dashboard

## Troubleshooting

### "Apple OAuth not configured" Error

- **Check**: `config/oauth.conf` exists and has values
- **Check**: `APPLE_CLIENT_ID` is not empty
- **Check**: API server was restarted after configuration changes
- **Check**: File permissions on `config/oauth.conf`

### "JWT library required for Apple OAuth" Error

- **Solution**: Install PyJWT: `pip install PyJWT`
- **Or**: Add to `api/requirements.txt` and reinstall dependencies

### OAuth callback fails

- **Check**: Redirect URI in config matches exactly what's configured in Apple Developer Portal
- **Check**: Domain is added to Apple Services ID configuration
- **Check**: Browser console for error messages
- **Check**: API server logs for detailed errors

### Private Key Format Issues

- **Ensure**: The private key includes the BEGIN/END markers
- **Ensure**: No extra spaces or line breaks (unless using multi-line format)
- **Test**: Try copying the key directly from the `.p8` file

## Security Best Practices

1. **Never commit `oauth.conf` to git** - Add it to `.gitignore`
2. **Use environment variables** in production instead of config files
3. **Rotate keys regularly** - Apple keys can be regenerated
4. **Use HTTPS in production** - OAuth requires secure connections
5. **Limit redirect URIs** - Only add the exact URIs you need

## Production Deployment

For production:

1. **Update redirect URIs** to use your production domain
2. **Use HTTPS** - OAuth providers require secure connections
3. **Update Apple Services ID** with production domain
4. **Consider using environment variables** instead of config files
5. **Set up proper domain verification** in Apple Developer Portal

## Additional Resources

- [Apple Sign in with Apple Documentation](https://developer.apple.com/sign-in-with-apple/)
- [Google OAuth 2.0 Documentation](https://developers.google.com/identity/protocols/oauth2)
- [Apple Developer Portal](https://developer.apple.com/account)
- [Google Cloud Console](https://console.cloud.google.com)
