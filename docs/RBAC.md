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
- Manage plugins and worlds
- View logs and metrics
- Manage players (whitelist, ban, op)

### Operator

**Server management access** - Operators can:

- View and control server status
- Create backups
- View backups
- Manage players (whitelist, ban, op)
- View logs and metrics
- View worlds and plugins
- View configuration files

**Cannot:**

- Restore or delete backups
- Manage users or roles
- Manage API keys
- Edit configuration files
- Manage plugins or worlds

### User

**Read-only access** - Regular users can:

- View server status
- View backups
- View players
- View logs and metrics
- View worlds and plugins
- View configuration files

**Cannot:**

- Control server (start, stop, restart)
- Create, restore, or delete backups
- Manage users or roles
- Manage API keys
- Edit configuration files
- Manage plugins or worlds
- Manage players

## Permissions

The system defines the following permissions:

### Server Permissions

- `server.view` - View server status and metrics
- `server.control` - Start, stop, restart server, send commands

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

API keys are granted **admin-level permissions** for backward compatibility. This means:

- API keys can access all endpoints
- API keys bypass permission checks
- API keys are treated as admin users

**Note:** This is intentional for programmatic access. If you need restricted API key access, use user authentication instead.

## Best Practices

1. **Principle of Least Privilege**: Assign users the minimum role necessary for their tasks
2. **Regular Audits**: Periodically review user roles and permissions
3. **Separate Accounts**: Use different accounts for different purposes (admin vs. operator)
4. **API Keys**: Use API keys for automation, but be aware they have full admin access
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
- [Security Guide](SECURITY.md) - Security best practices
