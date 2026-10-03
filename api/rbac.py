"""The permission model: what each permission means and what each role holds.

Pure data and functions with no dependency on the app or on who is logged in.
Deciding whether a request may proceed lives in ``api.auth_guard``.
"""

PERMISSIONS = {
    # Server control
    "server.view": "View server status",
    "server.control": "Control server (start/stop/restart)",
    "server.command": "Send commands to server",
    "server.manage": "Manage server configuration (properties, presets, announcements, schedules)",
    # Backup management
    "backup.create": "Create backups",
    "backup.restore": "Restore backups",
    "backup.delete": "Delete backups",
    "backup.view": "View backup list",
    # Configuration
    "config.view": "View configuration files",
    "config.edit": "Edit configuration files",
    # Deliberately granted to no role below except admin. The file browser
    # reads anything under data/, config/, backups/ and scripts/, which is
    # where every secret lives: users.json, api-keys.json, rcon.conf,
    # rcon.password in server.properties. While it only needed config.view,
    # any "user" account or key could read the admin API keys.
    "files.view": "Browse and download files in the file browser",
    # Player management
    "players.view": "View player list",
    "players.manage": "Manage players (ban/whitelist/op)",
    # World management
    "worlds.view": "View world list",
    "worlds.manage": "Manage worlds (create/delete/switch)",
    # Plugin management
    "plugins.view": "View plugin list",
    "plugins.manage": "Manage plugins (install/remove/enable/disable)",
    # Datapack management
    "datapacks.view": "View datapack list",
    "datapacks.manage": "Manage datapacks (install/remove/enable/disable)",
    # User management
    "users.view": "View user list",
    "users.manage": "Manage users (create/edit/delete/roles)",
    # API key management
    "api_keys.view": "View API keys",
    "api_keys.manage": "Manage API keys (create/delete/enable/disable)",
    # Logs
    "logs.view": "View server logs",
    # Admin only, like files.view: the audit log holds every account's IP
    # addresses, failed sign-ins and the commands people ran. It needed
    # logs.view, which the "user" role holds.
    "audit.view": "View the audit log",
    # Metrics
    "metrics.view": "View server metrics",
    "analytics.view": "View analytics and reports",
    "analytics.generate": "Generate analytics reports",
    # Settings
    "settings.view": "View application settings",
    "settings.edit": "Edit application settings",
    # The Oracle -- deliberately not granted to any role below except admin.
    # It spends real money on every allowlisted chat message and talks
    # directly to children; who can flip its kill switch or edit its
    # allowlist is a decision that should be made explicitly, not inherited
    # from a broader role's existing grants.
    "oracle.view": "View Oracle status and chat/quest log",
    "oracle.manage": "Manage the Oracle (enable/disable, allowlist, rate limit)",
}

# Role to permissions mapping
ROLE_PERMISSIONS = {
    "admin": list(PERMISSIONS.keys()),  # Admins have all permissions
    "user": [
        "server.view",
        "backup.view",
        "config.view",
        "players.view",
        "worlds.view",
        "plugins.view",
        "datapacks.view",
        "logs.view",
        "metrics.view",
        "analytics.view",
        "settings.view",
    ],
    "operator": [
        "server.view",
        "server.control",
        "server.command",
        "analytics.view",
        "analytics.generate",
        "backup.create",
        "backup.view",
        "backup.restore",
        "config.view",
        "players.view",
        "players.manage",
        "worlds.view",
        "plugins.view",
        "datapacks.view",
        "logs.view",
        "metrics.view",
        "settings.view",
    ],
}


# New API keys start here rather than at "admin": a key lives in a Shortcut, a
# browser or a script, so it is the credential most likely to leak.
DEFAULT_API_KEY_ROLE = "user"


def get_api_key_permissions(key_info):
    """Get the list of permissions an API key record grants.

    A key carries either an explicit ``permissions`` allowlist or a ``role``
    from the same ladder users use. Unknown permission names are dropped so a
    typo in the config file cannot widen a key's reach.
    """
    explicit = key_info.get("permissions")
    if isinstance(explicit, list):
        return [p for p in explicit if p in PERMISSIONS]
    key_role = key_info.get("role", DEFAULT_API_KEY_ROLE)
    return ROLE_PERMISSIONS.get(key_role, ROLE_PERMISSIONS[DEFAULT_API_KEY_ROLE])


def validate_api_key_scope(role, permissions):
    """Return an error string if a requested key scope is not usable, else None."""
    if role not in ROLE_PERMISSIONS:
        return f"Invalid role. Valid roles: {', '.join(ROLE_PERMISSIONS.keys())}"
    if permissions is None:
        return None
    if not isinstance(permissions, list) or not all(isinstance(p, str) for p in permissions):
        return "permissions must be a list of permission names"
    unknown = [p for p in permissions if p not in PERMISSIONS]
    if unknown:
        return f"Unknown permissions: {', '.join(sorted(unknown))}"
    return None
