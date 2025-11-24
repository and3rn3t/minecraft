# API Documentation Guide

This guide covers the REST API documentation for the Minecraft Server Management system.

## Overview

The API provides comprehensive endpoints for:

- Server control (start, stop, restart, commands)
- Backup management (create, list, restore, delete)
- Player management
- World and plugin management
- Configuration file management
- Monitoring and metrics
- User authentication and authorization
- API key management
- Dynamic DNS management

## OpenAPI Specification

The API is documented using OpenAPI 3.0 specification:

- **File**: `api/openapi.yaml`
- **Format**: YAML
- **Version**: 3.0.3

## Viewing Documentation

### Method 1: Swagger Editor (Online)

1. Go to [Swagger Editor](https://editor.swagger.io/)
2. Copy contents of `api/openapi.yaml`
3. Paste into editor
4. View interactive documentation

### Method 2: Swagger UI (Docker)

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

### Method 3: Using Script

```bash
# Serve API docs
./scripts/serve-api-docs.sh

# Or with custom port
PORT=9000 ./scripts/serve-api-docs.sh
```

### Method 4: Redoc

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

## API Base URL

- **Local**: `http://localhost:8080`
- **Raspberry Pi**: `http://minecraft-server.local:8080`
- **Production**: `https://your-domain.com:8080`

## Authentication

The API supports three authentication methods:

### 1. API Key (Recommended for Automation)

```bash
curl -H "X-API-Key: your-api-key" \
  http://localhost:8080/api/status
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

## Endpoint Categories

### Health Check

- `GET /api/health` - Check API health (no auth required)

### Authentication

- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login user
- `POST /api/auth/logout` - Logout user
- `GET /api/auth/me` - Get current user

### Server Control

- `GET /api/status` - Get server status
- `POST /api/server/start` - Start server
- `POST /api/server/stop` - Stop server
- `POST /api/server/restart` - Restart server
- `POST /api/server/command` - Send server command

### Backups

- `POST /api/backup` - Create backup
- `GET /api/backups` - List backups
- `POST /api/backups/{filename}/restore` - Restore backup
- `DELETE /api/backups/{filename}` - Delete backup

### Players

- `GET /api/players` - List players

### Worlds

- `GET /api/worlds` - List worlds

### Plugins

- `GET /api/plugins` - List plugins

### Configuration

- `GET /api/config/files` - List configuration files
- `GET /api/config/files/{filename}` - Get configuration file
- `POST /api/config/files/{filename}` - Update configuration file
- `POST /api/config/files/{filename}/validate` - Validate configuration file

### Logs

- `GET /api/logs` - Get server logs

### Metrics

- `GET /api/metrics` - Get server metrics

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

### Dynamic DNS

- `GET /api/ddns/status` - Get DDNS status
- `POST /api/ddns/update` - Update DDNS
- `GET /api/ddns/config` - Get DDNS configuration
- `POST /api/ddns/config` - Update DDNS configuration

## Example Requests

### Start Server

```bash
curl -X POST http://localhost:8080/api/server/start \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json"
```

### Create Backup

```bash
curl -X POST http://localhost:8080/api/backup \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json"
```

### Get Server Status

```bash
curl http://localhost:8080/api/status \
  -H "X-API-Key: your-api-key"
```

### Send Server Command

```bash
curl -X POST http://localhost:8080/api/server/command \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{"command": "say Hello from API"}'
```

### List Backups

```bash
curl http://localhost:8080/api/backups \
  -H "X-API-Key: your-api-key"
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

```json
{
  "error": "Error message",
  "code": "ERROR_CODE"
}
```

## Status Codes

- `200` - Success
- `201` - Created
- `400` - Bad Request
- `401` - Unauthorized
- `403` - Forbidden
- `404` - Not Found
- `500` - Internal Server Error

## Rate Limiting

Currently no rate limiting is implemented. Consider implementing for production use.

## CORS

CORS is enabled for all origins. Configure in `config/api.conf` for production.

## Updating Documentation

When adding new endpoints:

1. Update `api/openapi.yaml` with new endpoint
2. Add request/response schemas
3. Update this documentation
4. Test with Swagger UI

## Tools

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

## Resources

- [OpenAPI Specification](https://swagger.io/specification/)
- [Swagger Editor](https://editor.swagger.io/)
- [Swagger UI](https://swagger.io/tools/swagger-ui/)
- [Redoc](https://redocly.com/docs/redoc/)

## See Also

- [API Guide](API.md) - Detailed API usage guide
- [API Keys Guide](API_KEYS.md) - API key management
- [RBAC Guide](RBAC.md) - Role-based access control
