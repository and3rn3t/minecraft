"""File-browser path validation: the allowlist check every file route goes through.

The allowlist itself (``ALLOWED_FILE_PATHS``) and ``PROJECT_ROOT`` stay on
``api.server``, where the tests and the other consumers of ``PROJECT_ROOT``
patch them. They are read through the module at call time, never copied, so a
patched value is the one used here.
"""

import os
from pathlib import Path

from flask import jsonify

from api import server


def _within_allowed_roots(real_path):
    """Whether an already-resolved path sits inside one of the allowed roots.

    Written with os.path and a separator-terminated prefix rather than
    ``Path.is_relative_to``: the two are equivalent, but this form is one
    CodeQL recognises as a path sanitizer, so the file browser gets real
    analysis instead of a standing exemption.

    The trailing separator is what stops ``/srv/data-evil`` passing because it
    begins with ``/srv/data``.
    """
    for allowed_path in server.ALLOWED_FILE_PATHS:
        try:
            root = os.path.realpath(str(allowed_path))
        except (ValueError, OSError):
            continue
        if real_path == root or real_path.startswith(root + os.sep):
            return True
    return False


def is_path_allowed(file_path):
    """Check if a file path is within allowed directories"""
    try:
        return _within_allowed_roots(os.path.realpath(str(file_path)))
    except (ValueError, OSError):
        return False


def resolve_allowed_path(path_param):
    """Resolve a caller-supplied path and confirm it is inside an allowed root.

    Returns ``(path, None)`` when the path is usable, or ``(None, response)``
    with the refusal to return.

    Resolving first matters: ``.resolve()`` collapses ``..`` and follows
    symlinks, so a link inside an allowed directory pointing outside one is
    checked at its destination rather than by its name. Checking the string
    before resolving would miss that.

    The explicit rejections below are the paths that never reach the allowlist
    check at all, because resolving them raises first — a null byte used to
    surface as a 500 carrying the raw OS error.
    """
    if not isinstance(path_param, str) or "\x00" in path_param:
        return None, (jsonify({"error": "Invalid path"}), 400)

    try:
        candidate = os.path.realpath(os.path.join(str(server.PROJECT_ROOT), path_param))
    except (ValueError, OSError):
        return None, (jsonify({"error": "Invalid path"}), 400)

    if not _within_allowed_roots(candidate):
        return None, (jsonify({"error": "Path not allowed"}), 403)

    return Path(candidate), None
