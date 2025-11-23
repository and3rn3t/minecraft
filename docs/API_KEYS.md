# API Key Management

This document describes the API key management system for programmatic access to the Minecraft Server Management API.

## Overview

API keys provide a secure way to authenticate programmatic requests to the API without using user credentials. API keys are useful for:

- Automation scripts
- Webhooks
- External integrations
- CI/CD pipelines
- Monitoring tools

## Important Security Note

**API keys have full admin-level permissions** for backward compatibility. This means API keys can:

- Access all endpoints
- Perform all operations (server control, user management, etc.)
- Bypass permission checks

**Treat API keys as sensitive credentials** and store them securely.

## Creating API Keys

### Via Web Interface

1. Navigate to **API Keys** in the web interface
2. Click **Create API Key**
3. Enter a name and optional description
4. Click **Create Key**
5. **Copy and save the key immediately** - it will not be shown again

### Via API

**Endpoint:** `POST /api/keys`

**Permission Required:** `api_keys.manage` (admin only)

**Request Body:**

```json
{
  "name": "Webhook Integration",
  "description": "API key for webhook notifications"
}
```

**Response:**

```json
{
  "success": true,
  "key": "mc_1234567890abcdef1234567890abcdef12345678",
  "key_id": "mc_1234567890abcdef",
  "message": "API key created successfully"
}
```

**Important:** Save the full `key` value immediately. Only the `key_id` (preview) is stored and shown later.

## Using API Keys

### HTTP Header

Include the API key in the `X-API-Key` header:

```bash
curl -H "X-API-Key: mc_1234567890abcdef1234567890abcdef12345678" \
     http://localhost:8080/api/status
```

### JavaScript/Node.js

```javascript
const response = await fetch('http://localhost:8080/api/status', {
  headers: {
    'X-API-Key': 'mc_1234567890abcdef1234567890abcdef12345678',
  },
});
```

### Python

```python
import requests

headers = {
    'X-API-Key': 'mc_1234567890abcdef1234567890abcdef12345678'
}

response = requests.get('http://localhost:8080/api/status', headers=headers)
```

## Listing API Keys

**Endpoint:** `GET /api/keys`

**Permission Required:** `api_keys.view` (admin only)

**Response:**

```json
{
  "keys": [
    {
      "id": "mc_1234567890abcdef",
      "name": "Webhook Integration",
      "description": "API key for webhook notifications",
      "enabled": true,
      "created": "2025-01-15T10:30:00Z"
    }
  ]
}
```

**Note:** Only the key ID (preview) is shown, not the full key. This is for security.

## Managing API Keys

### Enable/Disable API Key

**Endpoints:**

- `PUT /api/keys/<key_id>/enable`
- `PUT /api/keys/<key_id>/disable`

**Permission Required:** `api_keys.manage` (admin only)

**Response:**

```json
{
  "success": true,
  "message": "API key enabled successfully"
}
```

**Use Cases:**

- Temporarily disable a key without deleting it
- Rotate keys by disabling old ones
- Revoke access quickly

### Delete API Key

**Endpoint:** `DELETE /api/keys/<key_id>`

**Permission Required:** `api_keys.manage` (admin only)

**Response:**

```json
{
  "success": true,
  "message": "API key deleted successfully"
}
```

**Warning:** Deleting an API key is permanent and cannot be undone.

## API Key Format

API keys follow this format:

```
mc_<32-character-hex-string>
```

Example: `mc_1234567890abcdef1234567890abcdef12345678`

- Prefix: `mc_` (Minecraft)
- Length: 40 characters total (3 prefix + 37 hex)
- Character set: Lowercase hexadecimal (0-9, a-f)

## Key Storage

API keys are stored in `config/api-keys.json`:

```json
{
  "mc_1234567890abcdef1234567890abcdef12345678": {
    "name": "Webhook Integration",
    "description": "API key for webhook notifications",
    "enabled": true,
    "created": "2025-01-15T10:30:00Z"
  }
}
```

**Security:**

- File permissions are set to 600 (owner read/write only)
- Keys are hashed in memory for comparison
- Full keys are never logged or exposed in responses

## Best Practices

### 1. Key Naming

Use descriptive names that indicate the key's purpose:

- ✅ `Webhook Integration`
- ✅ `CI/CD Pipeline`
- ✅ `Monitoring Tool`
- ❌ `key1`
- ❌ `test`

### 2. Key Rotation

Regularly rotate API keys:

1. Create a new key
2. Update your application to use the new key
3. Verify the new key works
4. Disable or delete the old key

### 3. Key Storage

**Never:**

- Commit API keys to version control
- Share keys in chat or email
- Hardcode keys in client-side code
- Store keys in plain text files

**Always:**

- Store keys in environment variables
- Use secret management tools
- Restrict file permissions
- Encrypt keys at rest

### 4. Key Scope

Since API keys have admin access, consider:

- Creating separate keys for different services
- Rotating keys if compromised
- Monitoring key usage
- Disabling unused keys

### 5. Key Lifecycle

- **Create**: Generate new key for new integration
- **Use**: Include in API requests
- **Monitor**: Track usage and errors
- **Rotate**: Periodically replace with new key
- **Disable**: Temporarily revoke access
- **Delete**: Permanently remove unused keys

## Examples

### Creating a Key for Webhook

```bash
curl -X POST http://localhost:8080/api/keys \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <admin-api-key>" \
  -d '{
    "name": "Webhook Service",
    "description": "API key for webhook notifications"
  }'
```

### Using Key in Script

```bash
#!/bin/bash
API_KEY="mc_1234567890abcdef1234567890abcdef12345678"
API_URL="http://localhost:8080"

# Check server status
curl -H "X-API-Key: $API_KEY" "$API_URL/api/status"

# Start server
curl -X POST -H "X-API-Key: $API_KEY" "$API_URL/api/server/start"
```

### Python Integration

```python
import os
import requests

API_KEY = os.environ.get('MINECRAFT_API_KEY')
API_URL = os.environ.get('MINECRAFT_API_URL', 'http://localhost:8080')

headers = {'X-API-Key': API_KEY}

# Get server status
response = requests.get(f'{API_URL}/api/status', headers=headers)
status = response.json()

# Create backup
if status.get('running'):
    requests.post(f'{API_URL}/api/backup', headers=headers)
```

## Troubleshooting

### "Invalid API Key" Error

1. Verify the key is correct (check for typos)
2. Ensure the key is enabled
3. Check that the key exists in `config/api-keys.json`
4. Verify file permissions allow reading

### "API Key Not Found" Error

- The key may have been deleted
- Check the key ID matches an existing key
- Verify the key format is correct

### Key Not Working After Creation

1. Ensure you saved the full key (not just the preview ID)
2. Check the key is enabled
3. Verify the key format matches: `mc_<32-hex-chars>`
4. Restart the API server if keys were added manually

## Security Considerations

1. **Full Admin Access**: API keys have admin permissions - treat them as admin credentials
2. **Key Exposure**: If a key is exposed, disable it immediately and create a new one
3. **Key Rotation**: Rotate keys periodically (every 90 days recommended)
4. **Key Monitoring**: Monitor API key usage for suspicious activity
5. **Key Storage**: Never store keys in plain text or version control
6. **Key Sharing**: Only share keys through secure channels
7. **Key Scope**: Use separate keys for different services to limit blast radius

## Comparison: API Keys vs User Authentication

| Feature         | API Keys       | User Authentication |
| --------------- | -------------- | ------------------- |
| **Permissions** | Admin (all)    | Role-based          |
| **Use Case**    | Automation     | Human users         |
| **Session**     | Stateless      | Session-based       |
| **Rotation**    | Manual         | Password change     |
| **Revocation**  | Disable/Delete | Disable account     |
| **Security**    | Single key     | Username + password |

**Recommendation:**

- Use **API keys** for automation, scripts, and integrations
- Use **user authentication** for human users with appropriate roles

## See Also

- [RBAC Documentation](RBAC.md) - Role-based access control
- [API Documentation](API.md) - Complete API reference
- [Security Guide](SECURITY.md) - Security best practices
