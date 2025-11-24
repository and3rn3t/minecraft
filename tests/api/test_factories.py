#!/usr/bin/env python3
"""
Tests for test data factories
"""

import pytest

from tests.api.factories import (
    create_api_key_data,
    create_backup_metadata,
    create_ban_entry,
    create_plugin_data,
    create_server_properties,
    create_user_data,
    create_whitelist_entry,
    create_world_data,
    generate_api_key,
)


def test_generate_api_key():
    """Test API key generation."""
    key = generate_api_key()
    assert len(key) == 40
    assert key.isalnum()

    # Test custom length
    key = generate_api_key(32)
    assert len(key) == 32


def test_create_user_data():
    """Test user data creation."""
    user = create_user_data()
    assert "username" in user
    assert "password" in user
    assert "email" in user
    assert user["role"] == "user"
    assert user["enabled"] is True

    # Test custom values
    user = create_user_data(username="custom", role="admin")
    assert user["username"] == "custom"
    assert user["role"] == "admin"


def test_create_api_key_data():
    """Test API key data creation."""
    key_data = create_api_key_data()
    assert "key" in key_data
    assert "name" in key_data
    assert "description" in key_data
    assert key_data["enabled"] is True
    assert len(key_data["key"]) == 40


def test_create_backup_metadata():
    """Test backup metadata creation."""
    metadata = create_backup_metadata()
    assert "name" in metadata
    assert "size" in metadata
    assert "world" in metadata
    assert "created" in metadata
    assert metadata["size"] > 0


def test_create_server_properties():
    """Test server.properties creation."""
    props = create_server_properties()
    assert "max-players=10" in props
    assert "view-distance=10" in props
    assert "difficulty=normal" in props

    # Test custom values
    props = create_server_properties(max_players=20, view_distance=12)
    assert "max-players=20" in props
    assert "view-distance=12" in props


def test_create_whitelist_entry():
    """Test whitelist entry creation."""
    entry = create_whitelist_entry("testuser")
    assert entry["name"] == "testuser"
    assert "uuid" in entry
    assert len(entry["uuid"]) == 36  # UUID format


def test_create_ban_entry():
    """Test ban entry creation."""
    entry = create_ban_entry("banneduser", "Test reason")
    assert entry["name"] == "banneduser"
    assert entry["reason"] == "Test reason"
    assert "uuid" in entry
    assert "expires" in entry


def test_create_world_data():
    """Test world data creation."""
    world = create_world_data()
    assert "name" in world
    assert "type" in world
    assert "seed" in world
    assert world["type"] == "default"


def test_create_plugin_data():
    """Test plugin data creation."""
    plugin = create_plugin_data()
    assert "name" in plugin
    assert "version" in plugin
    assert plugin["enabled"] is True
    assert plugin["version"] == "1.0.0"
