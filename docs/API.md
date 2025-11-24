# REST API Documentation

Complete guide to the REST API for remote Minecraft server management.

## Overview

The REST API provides HTTP endpoints for:

- Server control (start, stop, restart, commands)
- Server status and metrics
- Player management
- Backup operations
- World management
- Plugin management
- Configuration file management
- Log access
- User authentication and authorization
- API key management
- Dynamic DNS management

## Quick Start

### Enable API

1. **Configure API**:

   ```bash
   # Edit config/api.conf
   API_ENABLED=true
   API_HOST=127.0.0.1
   API_PORT=8080
   ```

2. **Create API Key**:

   ```bash
   ./scripts/api-key-manager.sh create webhook "Webhook integration"
   ```

3. **Start API Server**:

   ```bash
   ./scripts/api-server.sh start
   ```

4. **Test API**:
   ```bash
   curl -H "X-API-Key: YOUR_API_KEY" http://localhost:8080/api/health
   ```

## API Base URL

- **Local**: `http://localhost:8080`
- **Raspberry Pi**: `http://minecraft-server.local:8080`
- **Production**: `https://your-domain.com:8080`

## Authentication

The API supports three authentication methods. All endpoints (except `/api/health`) require authentication.

### 1. API Key (Recommended for Automation)

**Header Method** (Recommended):

```bash
curl -H "X-API-Key: YOUR_API_KEY" http://localhost:8080/api/status
```

**Query Parameter Method**:

```bash
curl http://localhost:8080/api/status?api_key=YOUR_API_KEY
```

### 2. Bearer Token (JWT)

```bash
# Login to get token
TOKEN=$(curl -X POST http://localhost:8080/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"password"}' \
  | jq -r '.token')

# Use token
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8080/api/status
```

### 3. Session Cookie

```bash
# Login (creates session)
curl -X POST http://localhost:8080/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"password"}' \
  -c cookies.txt

# Use session
curl -b cookies.txt http://localhost:8080/api/status
```

### API Key Management

**Create API Key**:

```bash
./scripts/api-key-manager.sh create <name> [description]
```

**List API Keys**:

```bash
./scripts/api-key-manager.sh list
```

**Disable API Key**:

```bash
./scripts/api-key-manager.sh disable <key-preview>
```

**Enable API Key**:

```bash
./scripts/api-key-manager.sh enable <key-preview>
```

**Delete API Key**:

```bash
./scripts/api-key-manager.sh delete <key-preview>
```

For more details, see [API Keys Guide](API_KEYS.md).

## OpenAPI Specification

The API is documented using OpenAPI 3.0 specification:

- **File**: `api/openapi.yaml`
- **Format**: YAML
- **Version**: 3.0.3

### Viewing Documentation

#### Method 1: Swagger Editor (Online)

1. Go to [Swagger Editor](https://editor.swagger.io/)
2. Copy contents of `api/openapi.yaml`
3. Paste into editor
4. View interactive documentation

#### Method 2: Swagger UI (Docker)

```bash
# Serve with Docker
docker run -d \
  --name swagger-ui \
  -p 8081:8080 \
  -e SWAGGER_JSON=/openapi.yaml \
  -v $(pwd)/api/openapi.yaml:/openapi.yaml:ro \
  swaggerapi/swagger-ui

# Open in browser
open http://localhost:8081
```

#### Method 3: Using Script

```bash
# Serve API docs
./scripts/serve-api-docs.sh

# Or with custom port
PORT=9000 ./scripts/serve-api-docs.sh
```

#### Method 4: Redoc

```bash
# Serve with Redoc
docker run -d \
  --name redoc \
  -p 8081:80 \
  -v $(pwd)/api/openapi.yaml:/usr/share/nginx/html/openapi.yaml:ro \
  redocly/redoc

# Open in browser
open http://localhost:8081
```

## API Endpoints

### Health Check

**GET** `/api/health`

Check if API is running (no authentication required).

**Response**:

```json
{
  "status": "healthy",
  "timestamp": "2025-01-15T10:30:00.000000",
  "version": "1.0.0"
}
```

### Authentication Endpoints

- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login user
- `POST /api/auth/logout` - Logout user
- `GET /api/auth/me` - Get current user

### Server Control

**GET** `/api/status`

Get server status.

**Response**:

```json
{
  "running": true,
  "status": "Up 2 hours",
  "timestamp": "2025-01-15T10:30:00.000000"
}
```

**POST** `/api/server/start`

Start the server.

**Response**:

```json
{
  "success": true,
  "message": "Server starting",
  "output": "..."
}
```

**POST** `/api/server/stop`

Stop the server.

**Response**:

```json
{
  "success": true,
  "message": "Server stopping",
  "output": "..."
}
```

**POST** `/api/server/restart`

Restart the server.

**Response**:

```json
{
  "success": true,
  "message": "Server restarting",
  "output": "..."
}
```

**POST** `/api/server/command`

Send a command to the server via RCON.

**Request Body**:

```json
{
  "command": "list"
}
```

**Response**:

```json
{
  "success": true,
  "response": "There are 2 of a max of 10 players online: Player1, Player2",
  "command": "list"
}
```

**Example Commands**:

- `"list"` - List online players
- `"say Hello World"` - Send message
- `"whitelist add PlayerName"` - Add to whitelist
- `"op PlayerName"` - Grant operator status
- `"save-all"` - Save world

### Backups

**POST** `/api/backup`

Create a server backup.

**Response**:

```json
{
  "success": true,
  "message": "Backup created",
  "output": "..."
}
```

**GET** `/api/backups`

List all backups.

**Response**:

```json
{
  "backups": [
    {
      "name": "minecraft_backup_20250115_103000.tar.gz",
      "size": 104857600,
      "created": "2025-01-15T10:30:00"
    }
  ],
  "count": 1
}
```

**POST** `/api/backups/{filename}/restore` - Restore backup

**DELETE** `/api/backups/{filename}` - Delete backup

### Players

**GET** `/api/players`

Get list of online players.

**Response**:

```json
{
  "players": ["Player1", "Player2"],
  "count": 2
}
```

### Worlds

**GET** `/api/worlds`

List all worlds.

**Response**:

```json
{
  "worlds": ["world", "survival", "creative"],
  "count": 3
}
```

### Plugins

**GET** `/api/plugins`

List installed plugins.

**Response**:

```json
{
  "plugins": ["EssentialsX", "WorldEdit"],
  "count": 2
}
```

### Configuration Files

- `GET /api/config/files` - List configuration files
- `GET /api/config/files/{filename}` - Get configuration file
- `POST /api/config/files/{filename}` - Update configuration file
- `POST /api/config/files/{filename}/validate` - Validate configuration file

### Logs

**GET** `/api/logs?lines=100`

Get server logs.

**Query Parameters**:

- `lines` - Number of lines to retrieve (default: 100)

**Response**:

```json
{
  "logs": [
    "[10:30:00] [Server thread/INFO] Starting minecraft server",
    "[10:30:01] [Server thread/INFO] Done!"
  ],
  "lines": 2
}
```

### Metrics

**GET** `/api/metrics`

Get server metrics.

**Response**:

```json
{
  "metrics": {
    "cpu_percent": "45.2",
    "memory_usage": "1.2GiB / 2.0GiB",
    "memory_percent": "60.0"
  },
  "timestamp": "2025-01-15T10:30:00.000000"
}
```

### API Keys

- `GET /api/keys` - List API keys
- `POST /api/keys` - Create API key
- `DELETE /api/keys/{key_id}` - Delete API key
- `PUT /api/keys/{key_id}/enable` - Enable API key
- `PUT /api/keys/{key_id}/disable` - Disable API key

### Users

- `GET /api/users` - List users
- `PUT /api/users/{username}/role` - Update user role
- `DELETE /api/users/{username}` - Delete user
- `PUT /api/users/{username}/enable` - Enable user
- `PUT /api/users/{username}/disable` - Disable user

For more details, see [RBAC Guide](RBAC.md).

### Dynamic DNS

- `GET /api/ddns/status` - Get DDNS status
- `POST /api/ddns/update` - Update DDNS
- `GET /api/ddns/config` - Get DDNS configuration
- `POST /api/ddns/config` - Update DDNS configuration

For more details, see [Dynamic DNS Guide](DYNAMIC_DNS.md).

## Usage Examples

### Python

```python
import requests

API_URL = "http://localhost:8080/api"
API_KEY = "your-api-key"

headers = {"X-API-Key": API_KEY}

# Get server status
response = requests.get(f"{API_URL}/status", headers=headers)
status = response.json()
print(f"Server running: {status['running']}")

# Send command
response = requests.post(
    f"{API_URL}/server/command",
    headers=headers,
    json={"command": "list"}
)
result = response.json()
print(result['response'])

# Start server
response = requests.post(f"{API_URL}/server/start", headers=headers)
print(response.json())
```

### cURL

```bash
# Set API key
API_KEY="your-api-key"
API_URL="http://localhost:8080/api"

# Get status
curl -H "X-API-Key: $API_KEY" "$API_URL/status"

# Send command
curl -X POST \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"command":"list"}' \
  "$API_URL/server/command"

# Create backup
curl -X POST \
  -H "X-API-Key: $API_KEY" \
  "$API_URL/backup"
```

### JavaScript/Node.js

```javascript
const axios = require('axios');

const API_URL = 'http://localhost:8080/api';
const API_KEY = 'your-api-key';

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'X-API-Key': API_KEY,
  },
});

// Get server status
async function getStatus() {
  const response = await api.get('/status');
  console.log(response.data);
}

// Send command
async function sendCommand(command) {
  const response = await api.post('/server/command', { command });
  console.log(response.data.response);
}

// Start server
async function startServer() {
  const response = await api.post('/server/start');
  console.log(response.data);
}
```

## Response Format

### Success Response

```json
{
  "success": true,
  "message": "Operation completed",
  "data": { ... }
}
```

### Error Response

All endpoints return standard HTTP status codes:

- `200 OK` - Request successful
- `201 Created` - Resource created
- `400 Bad Request` - Invalid request
- `401 Unauthorized` - Missing or invalid API key
- `403 Forbidden` - Insufficient permissions
- `404 Not Found` - Endpoint not found
- `500 Internal Server Error` - Server error

**Error Response Format**:

```json
{
  "error": "Error message",
  "code": "ERROR_CODE"
}
```

## API Server Management

### Start API Server

```bash
./scripts/api-server.sh start
```

### Stop API Server

```bash
./scripts/api-server.sh stop
```

### Restart API Server

```bash
./scripts/api-server.sh restart
```

### Check Status

```bash
./scripts/api-server.sh status
```

### View Logs

```bash
./scripts/api-server.sh logs
```

### Install Dependencies

```bash
./scripts/api-server.sh install-deps
```

## Configuration

Edit `config/api.conf`:

```bash
# Enable/disable API
API_ENABLED=true

# API host (127.0.0.1 for localhost only, 0.0.0.0 for all interfaces)
API_HOST=127.0.0.1

# API port
API_PORT=8080

# Enable CORS
CORS_ENABLED=true
```

## Security

### Best Practices

1. **Use Strong API Keys**: Let the system generate keys
2. **Restrict Access**: Use `127.0.0.1` for localhost-only access
3. **HTTPS**: Use reverse proxy (nginx) with SSL for production
4. **Firewall**: Don't expose API port to internet
5. **Key Rotation**: Regularly rotate API keys
6. **Disable Unused Keys**: Disable keys that are no longer needed

### Network Security

**Localhost Only** (Recommended):

```bash
API_HOST=127.0.0.1
```

**Local Network**:

```bash
API_HOST=0.0.0.0
# Use firewall to restrict access
```

**With Reverse Proxy**:

```nginx
# nginx configuration
location /api {
    proxy_pass http://127.0.0.1:8080;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
}
```

## Rate Limiting

Currently, the API does not implement rate limiting. For production use:

- Implement rate limiting in reverse proxy
- Monitor API usage
- Set appropriate limits per API key

## CORS

CORS is enabled for all origins by default. Configure in `config/api.conf` for production to restrict origins.

## Integration Examples

### Discord Bot

```python
import requests
import discord

API_URL = "http://localhost:8080/api"
API_KEY = "your-api-key"

@bot.command()
async def server_status(ctx):
    response = requests.get(
        f"{API_URL}/status",
        headers={"X-API-Key": API_KEY}
    )
    status = response.json()
    await ctx.send(f"Server: {'Online' if status['running'] else 'Offline'}")
```

### Monitoring Script

```bash
#!/bin/bash
# monitor-api.sh

API_URL="http://localhost:8080/api"
API_KEY="your-api-key"

# Check server status
STATUS=$(curl -s -H "X-API-Key: $API_KEY" "$API_URL/status" | jq -r '.running')

if [ "$STATUS" = "false" ]; then
    echo "Server is down! Starting..."
    curl -X POST -H "X-API-Key: $API_KEY" "$API_URL/server/start"
fi
```

### Webhook Example

```bash
#!/bin/bash
# webhook-example.sh

API_URL="http://localhost:8080/api"
API_KEY="your-api-key"

# Player joined webhook
curl -X POST \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"command":"say New player joined!"}' \
  "$API_URL/server/command"
```

## Developer Tools

### Generate Client Libraries

Use [OpenAPI Generator](https://openapi-generator.tech/):

```bash
# Generate Python client
openapi-generator generate \
  -i api/openapi.yaml \
  -g python \
  -o clients/python

# Generate JavaScript client
openapi-generator generate \
  -i api/openapi.yaml \
  -g javascript \
  -o clients/javascript
```

### Validate Specification

```bash
# Install swagger-cli
npm install -g @apidevtools/swagger-cli

# Validate
swagger-cli validate api/openapi.yaml
```

## Updating Documentation

When adding new endpoints:

1. Update `api/openapi.yaml` with new endpoint
2. Add request/response schemas
3. Update this documentation
4. Test with Swagger UI

## Troubleshooting

### API Server Won't Start

**Check Python**:

```bash
python3 --version
```

**Install Dependencies**:

```bash
./scripts/api-server.sh install-deps
```

**Check Logs**:

```bash
./scripts/api-server.sh logs
cat logs/api-server.log
```

### Authentication Fails

**Verify API Key**:

```bash
./scripts/api-key-manager.sh list
```

**Check Key is Enabled**:

```bash
./scripts/api-key-manager.sh enable <key-preview>
```

### Connection Refused

**Check API is Running**:

```bash
./scripts/api-server.sh status
```

**Check Port**:

```bash
netstat -tlnp | grep 8080
```

**Check Configuration**:

```bash
cat config/api.conf
```

## Resources

- [OpenAPI Specification](https://swagger.io/specification/)
- [Swagger Editor](https://editor.swagger.io/)
- [Swagger UI](https://swagger.io/tools/swagger-ui/)
- [Redoc](https://redocly.com/docs/redoc/)
- [OpenAPI Generator](https://openapi-generator.tech/)

## See Also

- [QUICK_REFERENCE.md](QUICK_REFERENCE.md) - Command reference
- [API_KEYS.md](API_KEYS.md) - API key management
- [RBAC.md](RBAC.md) - Role-based access control
- [RCON.md](RCON.md) - RCON guide
- [DYNAMIC_DNS.md](DYNAMIC_DNS.md) - Dynamic DNS integration
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Troubleshooting guide
