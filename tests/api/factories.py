"""
Test Data Factories
Reusable factories for creating test data
"""

import secrets
import string
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional


def generate_api_key(length: int = 40) -> str:
    """Generate a random API key."""
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def create_user_data(
    username: Optional[str] = None,
    password: Optional[str] = None,
    email: Optional[str] = None,
    role: str = "user",
    enabled: bool = True,
) -> Dict:
    """Create test user data."""
    if username is None:
        username = f"testuser_{secrets.token_hex(4)}"
    if password is None:
        password = "testpassword123"
    if email is None:
        email = f"{username}@test.example.com"

    return {"username": username, "password": password, "email": email, "role": role, "enabled": enabled}


def create_api_key_data(
    name: Optional[str] = None, description: Optional[str] = None, enabled: bool = True, key: Optional[str] = None
) -> Dict:
    """Create test API key data."""
    if name is None:
        name = f"test-key-{secrets.token_hex(4)}"
    if description is None:
        description = "Test API key"
    if key is None:
        key = generate_api_key()

    return {
        "key": key,
        "name": name,
        "description": description,
        "enabled": enabled,
        "created": datetime.now(timezone.utc).isoformat() + "Z",
    }


def create_backup_metadata(
    backup_name: Optional[str] = None, size: Optional[int] = None, world_name: str = "world"
) -> Dict:
    """Create test backup metadata."""
    if backup_name is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"minecraft_backup_{timestamp}.tar.gz"
    if size is None:
        size = 1024 * 1024  # 1MB default

    return {
        "name": backup_name,
        "size": size,
        "world": world_name,
        "created": datetime.now(timezone.utc).isoformat() + "Z",
        "type": "manual",
    }


def create_server_properties(
    max_players: int = 10, view_distance: int = 10, difficulty: str = "normal", gamemode: str = "survival"
) -> str:
    """Create test server.properties content."""
    return f"""# Minecraft Server Properties
max-players={max_players}
view-distance={view_distance}
difficulty={difficulty}
gamemode={gamemode}
motd=Test Minecraft Server
pvp=true
online-mode=false
"""


def create_whitelist_entry(username: str, uuid: Optional[str] = None) -> Dict:
    """Create test whitelist entry."""
    if uuid is None:
        # Standard UUID format: 8-4-4-4-12 hex characters (36 chars total)
        import uuid as uuid_lib

        uuid = str(uuid_lib.uuid4())

    return {"uuid": uuid, "name": username}


def create_ban_entry(username: str, reason: str = "Test ban", expires: Optional[str] = None) -> Dict:
    """Create test ban entry."""
    now = datetime.now(timezone.utc)
    if expires is None:
        expires = (now + timedelta(days=1)).isoformat() + "Z"

    # Use standard UUID format
    import uuid as uuid_lib

    uuid = str(uuid_lib.uuid4())

    return {
        "uuid": uuid,
        "name": username,
        "created": now.isoformat() + "Z",
        "source": "Server",
        "expires": expires,
        "reason": reason,
    }


def create_world_data(
    world_name: Optional[str] = None, world_type: str = "default", seed: Optional[int] = None
) -> Dict:
    """Create test world data."""
    if world_name is None:
        world_name = f"test_world_{secrets.token_hex(4)}"
    if seed is None:
        seed = secrets.randbelow(1000000)

    return {
        "name": world_name,
        "type": world_type,
        "seed": seed,
        "created": datetime.now(timezone.utc).isoformat() + "Z",
    }


def create_plugin_data(plugin_name: Optional[str] = None, version: str = "1.0.0", enabled: bool = True) -> Dict:
    """Create test plugin data."""
    if plugin_name is None:
        plugin_name = f"TestPlugin_{secrets.token_hex(4)}"

    return {
        "name": plugin_name,
        "version": version,
        "enabled": enabled,
        "author": "Test Author",
        "description": "Test plugin description",
    }
