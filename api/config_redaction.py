"""Helpers for showing config files without leaking what is in them.

Pure functions with no dependency on the app, so they can be tested and reused
without importing ``api.server``.
"""

import re


def describe_yaml_error(error):
    """Describe a YAML parse failure using only the parser's own fields.

    str(a YAMLError) formats the problem together with the surrounding context
    and the stream name. Taking `problem` and `problem_mark` keeps what the
    caller needs — what is wrong and where — without passing the exception's
    rendering through to the response.
    """
    problem = getattr(error, "problem", None) or "could not be parsed"
    mark = getattr(error, "problem_mark", None)
    if mark is not None:
        # Marks are zero-based; editors are not.
        return f"Invalid YAML: {problem} (line {mark.line + 1}, column {mark.column + 1})"
    return f"Invalid YAML: {problem}"


# Keys whose values are credentials: rcon.password, SECRET_KEY,
# CLOUDFLARE_API_TOKEN, NOIP_PASSWORD, ANTHROPIC_API_KEY and the like.
_SECRET_KEY_PATTERN = re.compile(r"pass|secret|token|api[_.-]?key|private[_.-]?key|credential", re.IGNORECASE)
# `key=value` (.properties, .conf, compose list entries) or `key: value` (YAML).
# The value may be empty: in YAML that opens a nested block.
_CONFIG_LINE_PATTERN = re.compile(r"^(\s*(?:-\s*)?(?:export\s+)?)([A-Za-z0-9_.\-]+)(\s*[=:])(\s*)(.*)$")
# A YAML block scalar header: `|`, `>`, optionally with chomping/indent indicators
_YAML_BLOCK_SCALAR = re.compile(r"^[|>][0-9+-]*\s*(#.*)?$")
REDACTED_VALUE = "********"


def _indent(line):
    return len(line) - len(line.lstrip())


def redact_config_secrets(content):
    """Replace credential values in config text, leaving everything else intact.

    Returns ``(content, redacted)``. config.view is held by every role, and
    these files carry the RCON password, the session signing key and the
    Cloudflare token; reading them used to be enough to take over the server.

    A value can span lines, and all of it is withheld: a YAML block scalar
    (``KEY: |``) or nested block under ``KEY:``, whose lines are those indented
    deeper than the key; or a quoted .conf value (``KEY="...``) running to its
    closing quote. Those continuation lines are dropped, leaving the masked key.
    """
    redacted = False
    lines = []
    block_indent = None  # indent of a masked key whose indented block is being skipped
    open_quote = None  # quote character of a masked value still running on

    for line in content.split("\n"):
        if open_quote is not None:
            if open_quote in line:
                open_quote = None
            continue

        if block_indent is not None:
            if not line.strip():
                continue
            if _indent(line) > block_indent:
                redacted = True
                continue
            block_indent = None

        match = _CONFIG_LINE_PATTERN.match(line)
        # Comments never match: "#" is not a key character
        if match and _SECRET_KEY_PATTERN.search(match.group(2)):
            prefix, key, separator, space, value = match.groups()
            value = value.strip()
            if not value or _YAML_BLOCK_SCALAR.match(value):
                # The value is whatever is indented below, if anything is
                block_indent = _indent(line)
                if value:
                    lines.append(f"{prefix}{key}{separator}{space}{REDACTED_VALUE}")
                    redacted = True
                else:
                    lines.append(line)
                continue
            if value[0] in "\"'" and value[1:].find(value[0]) == -1:
                open_quote = value[0]
            lines.append(f"{prefix}{key}{separator}{space}{REDACTED_VALUE}")
            redacted = True
            continue

        lines.append(line)

    return "\n".join(lines), redacted
