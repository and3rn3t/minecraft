"""
Security utilities for the Minecraft Server API
Includes input validation, sanitization, and security helpers
"""

import re
from typing import Optional, Tuple

# Dangerous command patterns that should be blocked
DANGEROUS_COMMAND_PATTERNS = [
    # Shell metacharacters. Not whitespace: commands reach the server as a
    # single argv element (api/rcon.py, or rcon-client.sh's quoted "$command")
    # and never pass through a shell, and blocking spaces refused every
    # command that takes an argument ("say hello", "kick alice").
    r"[;&|`$(){}[\]<>]",
    r"\.\.",  # Path traversal
    r"\/etc\/",  # System directories
    r"\/proc\/",  # System directories
    r"\/sys\/",  # System directories
    r"rm\s+-rf",  # Dangerous rm command
    r"mkfs",  # File system formatting
    r"dd\s+if=",  # Disk operations
    r"wget\s+",  # Downloading files
    r"curl\s+",  # Downloading files
]

# Allowed Minecraft server commands (whitelist approach)
ALLOWED_MINECRAFT_COMMANDS = {
    "kick",
    "ban",
    "pardon",
    "op",
    "deop",
    "whitelist",
    "give",
    "tp",
    "teleport",
    "gamemode",
    "time",
    "weather",
    "difficulty",
    "gamerule",
    "say",
    "tell",
    "me",
    "title",
    "subtitle",
    "actionbar",
    "clear",
    "effect",
    "enchant",
    "fill",
    "clone",
    "setblock",
    "summon",
    "kill",
    "spawnpoint",
    "setworldspawn",
    "save-all",
    "save-off",
    "save-on",
    "stop",
    "restart",
    "reload",
    "seed",
    "list",
    "help",
    "version",
    "msg",
    "team",
    "scoreboard",
    "advancement",
    "bossbar",
    "execute",
    "forceload",
    "function",
    "locate",
    "particle",
    "playsound",
    "recipe",
    "schedule",
    "spreadplayers",
    "stopsound",
    "tag",
    "teammsg",
    "trigger",
    "w",
    "xp",
}

# Blocked command prefixes (blacklist approach)
BLOCKED_COMMAND_PREFIXES = [
    "/",  # Prevent shell commands
    "sudo",
    "su",  # Privilege escalation
    "sh",
    "bash",
    "zsh",
    "csh",  # Shell invocations
    "python",
    "python3",
    "node",
    "npm",  # Script execution
]


def sanitize_minecraft_command(command: str) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Sanitize and validate a Minecraft server command.

    Args:
        command: The command string to validate

    Returns:
        Tuple of (is_valid, sanitized_command, error_message)
    """
    if not command:
        return False, None, "Command cannot be empty"

    # Remove leading slash if present (Minecraft commands can have /)
    command = command.lstrip("/").strip()

    if not command:
        return False, None, "Command cannot be empty"

    # Check for dangerous patterns
    for pattern in DANGEROUS_COMMAND_PATTERNS:
        if re.search(pattern, command, re.IGNORECASE):
            return False, None, f"Command contains potentially dangerous pattern: {pattern}"

    # Check for blocked commands. The whole first word is compared: matching
    # it as a prefix made "su" refuse "summon" and "subtitle".
    first_word = command.split()[0].lower() if command.split() else ""
    for blocked in BLOCKED_COMMAND_PREFIXES:
        if first_word == blocked.lower():
            return False, None, f"Command '{blocked}' is not allowed"

    # Whitelist check - if command list is provided, validate against it
    # Allow any command that doesn't match dangerous patterns and starts with allowed prefix
    # This is more permissive but safer than allowing everything

    # Additional validation: ensure no shell injection
    # Escape special characters that could be used for injection
    # But preserve the command structure for Minecraft

    # Limit command length (Minecraft has limits but we'll be more restrictive)
    if len(command) > 256:
        return False, None, "Command exceeds maximum length of 256 characters"

    return True, command, None


def sanitize_string(input_str: str, max_length: int = 1000, allow_newlines: bool = False) -> str:
    """
    Sanitize a string input to prevent XSS and injection attacks.

    Args:
        input_str: The string to sanitize
        max_length: Maximum allowed length
        allow_newlines: Whether to allow newline characters

    Returns:
        Sanitized string
    """
    if not isinstance(input_str, str):
        return ""

    # Truncate if too long
    if len(input_str) > max_length:
        input_str = input_str[:max_length]

    # Remove null bytes
    input_str = input_str.replace("\x00", "")

    # Remove newlines if not allowed
    if not allow_newlines:
        input_str = input_str.replace("\n", " ").replace("\r", " ")

    # Remove control characters (except tabs and newlines if allowed)
    cleaned = ""
    for char in input_str:
        if ord(char) < 32:
            if allow_newlines and char in "\n\r":
                cleaned += char
            elif char == "\t":
                cleaned += char
        else:
            cleaned += char

    return cleaned.strip()


def sanitize_for_json(value) -> str:
    """
    Sanitize a value for safe inclusion in JSON responses.
    Prevents XSS through JSON injection.

    Args:
        value: The value to sanitize

    Returns:
        Sanitized string representation
    """
    import json

    # Use json.dumps to safely escape the value
    return json.dumps(str(value))[1:-1]  # Remove surrounding quotes


def sanitize_for_log(value, limit: int = 4000) -> str:
    """
    Make untrusted, possibly multi-line text (a script's stderr) safe to write to a log.

    Newlines and tabs are kept, because a traceback is the point, but every other
    control character is dropped (NULs, carriage returns and escape sequences can
    overwrite or colour what a reader sees). Continuation lines are indented, so text
    that imitates a log entry cannot start at column zero, and the result is capped
    at ``limit`` characters.

    Args:
        value: The text (or bytes) to sanitize
        limit: The most characters to keep

    Returns:
        A string safe to pass as a logging argument
    """
    text = value.decode("utf-8", errors="replace") if isinstance(value, bytes) else str(value)
    text = "".join(ch for ch in text if ch in "\n\t" or ch.isprintable())
    truncated = len(text) - limit
    if truncated > 0:
        text = text[:limit] + f"... [{truncated} more characters]"
    return text.replace("\n", "\n    ")


def is_rate_limit_exceeded(identifier: str, limit: int, window: int, storage: dict) -> bool:
    """
    Simple in-memory rate limiting check.
    For production, use a proper rate limiting library like Flask-Limiter.

    Args:
        identifier: Unique identifier (IP, user, etc.)
        limit: Maximum number of requests
        window: Time window in seconds
        storage: Dictionary to store rate limit data

    Returns:
        True if rate limit exceeded, False otherwise
    """
    import time

    now = time.time()
    key = f"ratelimit:{identifier}"

    if key not in storage:
        storage[key] = {"count": 1, "window_start": now}
        return False

    rate_data = storage[key]

    # Reset window if expired
    if now - rate_data["window_start"] > window:
        rate_data["count"] = 1
        rate_data["window_start"] = now
        return False

    # Increment count
    rate_data["count"] += 1

    # Check if limit exceeded
    return rate_data["count"] > limit
