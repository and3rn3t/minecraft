# Role-Based Access Control (RBAC)

This document describes the Role-Based Access Control (RBAC) system implemented in the Minecraft Server Management API.

## Overview

The RBAC system provides fine-grained permission control for different user roles. Each role has a specific set of permissions that determine what actions users can perform in the system.

## Roles

The system defines three default roles:

### Admin

**Full system access** - Admins have all permissions and can:

- View and control server status
- Manage backups (create, restore, delete)
- Manage users and roles
- Manage API keys
- Edit configuration files
- Manage plugins, worlds and datapacks
- View logs and metrics
- Manage players (whitelist, ban, op)

### Operator

**Server management access** - Operators can:

- View and control server status
- Create backups
- View backups
- Manage players (whitelist, ban, op)
- View logs and metrics
- View worlds, plugins and datapacks
- View configuration files

**Cannot:**

- Restore or delete backups
- Manage users or roles
- Manage API keys
- Edit configuration files
- Manage plugins, worlds or datapacks

### User

**Read-only access** - Regular users can:

- View server status
- View backups
- View players
- View logs and metrics
- View worlds, plugins and datapacks
- View configuration files

**Cannot:**

- Control server (start, stop, restart)
- Create, restore, or delete backups
- Manage users or roles
- Manage API keys
- Edit configuration files
- Manage plugins, worlds or datapacks
- Manage players

## Permissions

The system defines the following permissions:

### Server Permissions

- `server.view` - View server status and metrics
- `server.control` - Start, stop, restart the server
- `server.command` - Send commands to the server, over REST or the log socket
- `server.manage` - Manage server configuration: properties, performance
  presets, announcements and scheduled commands. Included in the `admin` role by
  default; it may also be granted explicitly in an API key's `permissions` array.

### Backup Permissions

- `backup.view` - List backups
- `backup.create` - Create new backups
- `backup.restore` - Restore backups
- `backup.delete` - Delete backups

### Configuration Permissions

- `config.view` - View configuration files
- `config.edit` - Edit and validate configuration files

### Player Permissions

- `players.view` - List online players
- `players.manage` - Whitelist, ban, op players

### World Permissions

- `worlds.view` - List worlds
- `worlds.manage` - Create, delete, switch worlds

### Plugin Permissions

- `plugins.view` - List plugins
- `plugins.manage` - Install, update, enable, disable plugins

### Datapack Permissions

- `datapacks.view` - List datapacks
- `datapacks.manage` - Install, enable, disable, delete datapacks

### Log Permissions

- `logs.view` - View server logs

### Metrics Permissions

- `metrics.view` - View server performance metrics

### API Key Permissions

- `api_keys.view` - List API keys
- `api_keys.manage` - Create, delete, enable, disable API keys

### User Management Permissions

- `users.view` - List users and roles
- `users.manage` - Create, delete, enable, disable users, change roles

### Settings Permissions

- `settings.view` - View application settings
- `settings.edit` - Edit application settings

## Permission Checking

Permissions are checked automatically by the `@require_permission` decorator on API endpoints. The system checks:

1. If the user is authenticated (via session or API key)
2. If the user's role has the required permission
3. If the user is enabled

### Example

```python
@app.route('/api/server/start', methods=['POST'])
@require_permission("server.control")
def start_server():
    # Only users with server.control permission can access this
    ...
```

## User Management

### Registration and the first account

`POST /api/auth/register` creates the **bootstrap account** — the first user on
a fresh server, which is given the `admin` role so there is someone who can
manage everyone else. Once that account exists the endpoint returns `403` and
further accounts are created by an admin through `POST /api/users`.

Set `REGISTRATION_ENABLED=true` in the environment to keep open registration on
anyway. Accounts created that way get the `user` role, never `admin`.

### Creating Users

**Endpoint:** `POST /api/users`

**Permission Required:** `users.manage`

**Request Body:**

```json
{
  "username": "silas",
  "password": "a-long-password",
  "email": "silas@example.com",
  "role": "user"
}
```

`role` is optional and defaults to `user`. It must be one of `admin`,
`operator` or `user`.

**Response:** `201 Created`

```json
{
  "success": true,
  "message": "User created",
  "user": { "username": "silas", "role": "user" }
}
```

### Viewing Users

**Endpoint:** `GET /api/users`

**Permission Required:** `users.view`

**Response:**

```json
{
  "users": [
    {
      "username": "admin",
      "role": "admin",
      "email": "admin@example.com",
      "enabled": true,
      "created": "2025-01-15T00:00:00Z"
    }
  ]
}
```

### Updating User Role

**Endpoint:** `PUT /api/users/<username>/role`

**Permission Required:** `users.manage`

**Request Body:**

```json
{
  "role": "operator"
}
```

**Response:**

```json
{
  "success": true,
  "message": "User role updated successfully"
}
```

### Enabling/Disabling Users

**Endpoints:**

- `PUT /api/users/<username>/enable`
- `PUT /api/users/<username>/disable`

**Permission Required:** `users.manage`

**Response:**

```json
{
  "success": true,
  "message": "User enabled successfully"
}
```

### Deleting Users

**Endpoint:** `DELETE /api/users/<username>`

**Permission Required:** `users.manage`

**Safety Checks:**

- Cannot delete the last admin user
- Cannot delete your own account

**Response:**

```json
{
  "success": true,
  "message": "User deleted successfully"
}
```

## Permission Endpoints

### Get Current User Permissions

**Endpoint:** `GET /api/permissions`

**Permission Required:** Authentication only

**Response:**

```json
{
  "username": "admin",
  "role": "admin",
  "permissions": [
    "server.view",
    "server.control",
    "backup.view",
    ...
  ]
}
```

### Get All Roles

**Endpoint:** `GET /api/roles`

**Permission Required:** Authentication only

**Response:**

```json
{
  "roles": {
    "admin": {
      "permissions": [...],
      "permission_count": 25
    },
    "operator": {
      "permissions": [...],
      "permission_count": 12
    },
    "user": {
      "permissions": [...],
      "permission_count": 6
    }
  }
}
```

## API Key Permissions

API keys carry a role from the same ladder users do, and are checked by the same
`has_permission()`. A key's role is set when it is created — defaulting to `user`
— and changed later with `PUT /api/keys/<key_id>`.

A key may also carry an explicit `permissions` array, which takes precedence over
its role. That is the right shape for a key that does exactly one thing: a Siri
Shortcut that only starts the server needs `server.control`, nothing more.

Keys created before scoping existed have no role recorded. They are treated as
`admin` so nothing breaks, and the API server warns about them on startup.
Narrow them from the API Keys page. See [API_KEYS.md](API_KEYS.md).

A key whose role is `admin` reaches everything an admin user reaches, and is
not held to the `PERMISSIONS` list. A key carrying an explicit `permissions`
array is held to that array whatever its role, so narrowing a key by listing
its permissions always wins.

The WebSocket log stream is scoped too: connecting needs `logs.view`, and running
a command over that socket needs `server.command`.

## Best Practices

1. **Principle of Least Privilege**: Assign users the minimum role necessary for their tasks
2. **Regular Audits**: Periodically review user roles and permissions
3. **Separate Accounts**: Use different accounts for different purposes (admin vs. operator)
4. **API Keys**: Scope each key to the smallest role that does its job, especially keys that live on a phone or in a browser
5. **User Management**: Keep at least one admin account enabled at all times

## Security Considerations

1. **Role Assignment**: Only admins can change user roles
2. **Last Admin Protection**: The system prevents disabling or deleting the last admin user
3. **Self-Protection**: Users cannot modify or delete their own accounts
4. **Permission Inheritance**: Permissions are inherited from roles, not assigned individually
5. **Session Management**: Permissions are checked on every request

## Troubleshooting

### "Permission Denied" Errors

If you receive a 403 (Forbidden) error:

1. Check your current role: `GET /api/permissions`
2. Verify the endpoint requires a permission you have
3. Ensure your account is enabled
4. Contact an admin to update your role if needed

### Cannot Change User Role

- Ensure you have `users.manage` permission (admin role)
- Verify the target user exists
- Check that the new role is valid (admin, operator, user)

### Cannot Delete User

- Ensure you have `users.manage` permission
- Verify you're not trying to delete the last admin
- Check that you're not trying to delete your own account

## Examples

### Checking Permissions in Frontend

```javascript
// Get current user permissions
const response = await api.getPermissions();
const { role, permissions } = response;

// Check if user can perform action
if (permissions.includes('server.control')) {
  // Show server control buttons
}
```

### Updating User Role

```javascript
// Update user role to operator
await api.updateUserRole('username', 'operator');
```

### Listing All Users

```javascript
// Get all users (requires users.view permission)
const response = await api.listUsers();
const users = response.users;

// Filter by role
const admins = users.filter(u => u.role === 'admin');
```

## See Also

- [API Documentation](API.md) - Complete API reference
- [Web Interface Guide](WEB_INTERFACE.md) - Web UI documentation
- [Security Hardening](SECURITY_HARDENING.md) - Security best practices
