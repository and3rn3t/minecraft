"""Real-time log streaming and the WebSocket console.

One follower thread streams the Minecraft container's log, feeds every line to
the game event bus, and fans lines out to the clients subscribed over
Socket.IO. The handlers authenticate each connection once, at connect, then
re-check the live permissions of that identity on every later message.

The Socket.IO instance, the accounts and API keys, the RCON runner and the
audit logger live on ``api.server`` and are read through it at call time, so a
value patched there is the one used here. Importing this module is safe without
Flask-SocketIO; the handlers are then simply never registered.
"""

import subprocess
import threading

from flask import request

from api import auth_crypto, auth_guard, rbac, server
from api.security import sanitize_minecraft_command, sanitize_string

try:
    from flask_socketio import disconnect
except ImportError:  # Flask-SocketIO is optional
    disconnect = None


def _on(event):
    """Register a Socket.IO handler, or leave the function alone without Socket.IO."""
    if server.socketio is None:
        return lambda handler: handler
    return server.socketio.on(event)


# Session ids currently subscribed to the log stream
active_log_streams = set()
# sid -> the identity that opened that connection, as ("api_key", key) or
# ("user", username). The socket authenticates once at connect, so later
# messages on the same connection are checked against the identity
# recorded here. The identity itself is stored rather than its resolved
# permissions, so narrowing, disabling or deleting a key or user takes
# effect on sockets it already opened instead of only on the next
# connection.
_stream_keys = {}
_log_streams_lock = threading.Lock()
# Mutable holder rather than a module-level bool, so the reader and the
# starter share one piece of state without `global` declarations. The
# follower no longer stops when the last client disconnects, so `stop` is
# what shutdown and the tests use to bring it down deliberately.
_log_reader_state = {"running": False, "stop": False, "proc": None}

LOG_BACKLOG_LINES = 200


def get_log_tail(lines=100):
    """Get last N lines of server logs"""
    try:
        result = subprocess.run(
            ["docker", "logs", "--tail", str(lines), "minecraft-server"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.split("\n")
        return []
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return []


def _publish_log_line(line):
    """Feed one log line to the event bus, returning the event or None.

    Persistence failures and handler errors are contained by the bus itself;
    this wrapper exists so that a bus problem can never stop log streaming.
    """
    if not server.EVENTS_AVAILABLE:
        return None
    try:
        return server.game_events.get_bus().handle_line(line)
    except Exception as exc:  # noqa: BLE001 - streaming must outlive the bus
        server.app.logger.error(f"Event bus failed on a log line: {exc}")
        return None


def _log_reader():
    """Follow the container log, fan lines out, and drive the event bus.

    The previous implementation gave every client its own thread that ran
    `docker logs --tail 50` every second and diffed the result against the
    last batch, which scaled badly, missed lines that scrolled past between
    polls, and duplicated any line that legitimately repeated. One follower
    process streams the log instead, so lines arrive in order, exactly once.

    It now also runs whether or not anybody is watching. The log is the only
    real-time signal the Minecraft server produces, so a follower that
    started on the first browser connection and stopped on the last one
    meant every death, advancement and chat message that happened with the
    dashboard closed was lost. Events are parsed and recorded continuously;
    the WebSocket fanout is just one consumer of them.

    It attaches with `--tail 0` deliberately. Because every line read here
    is persisted as an event, replaying a backlog would record the same
    deaths and advancements again on every API restart and every re-attach,
    and the counts would climb with each one. New clients still get their
    scrollback: `handle_connect` sends `get_log_tail()` separately, and that
    path does not touch the bus. The trade is that events occurring while
    the API is down are not captured, which is far better than recording
    some of them repeatedly.
    """
    # `stop` is read here without the lock on purpose. It is a single boolean
    # that stop_log_reader() sets (under the lock) and that is only ever read
    # for its current value, so a stale read costs at most one more pass of
    # this loop. stop_log_reader() also kills the `docker logs` process, which
    # is what actually wakes a reader blocked in the read below. The lock is
    # for the compound check-and-set in ensure_log_reader().
    while not _log_reader_state["stop"]:
        proc = None
        try:
            proc = subprocess.Popen(
                ["docker", "logs", "-f", "--tail", "0", "minecraft-server"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
            with _log_streams_lock:
                _log_reader_state["proc"] = proc

            for line in proc.stdout:
                if _log_reader_state["stop"]:
                    break

                line = line.rstrip("\n")
                if not line.strip():
                    continue

                # Parse and persist first, so an event is recorded even if
                # no client is connected to receive it.
                event = _publish_log_line(line)

                with _log_streams_lock:
                    subscribers = list(active_log_streams)
                for sid in subscribers:
                    server.socketio.emit("logs", {"logs": [line], "type": "update"}, room=sid)
                    if event is not None:
                        server.socketio.emit("game_event", event.to_dict(), room=sid)
        except FileNotFoundError:
            # Docker is not installed; there is nothing to stream
            with _log_streams_lock:
                subscribers = list(active_log_streams)
            for sid in subscribers:
                server.socketio.emit("error", {"message": "Docker is not available"}, room=sid)
            with _log_streams_lock:
                _log_reader_state["running"] = False
            return
        except Exception as e:  # noqa: BLE001 - surfaced to the client below
            with _log_streams_lock:
                subscribers = list(active_log_streams)
            server.app.logger.error(f"Log streaming error: {e}")
            for sid in subscribers:
                server.socketio.emit("error", {"message": "Log streaming error"}, room=sid)
        finally:
            with _log_streams_lock:
                _log_reader_state["proc"] = None
            if proc is not None:
                try:
                    proc.kill()
                except OSError:
                    # Best effort: the process has usually exited on its
                    # own by this point, and failing to reap it must not
                    # stop the reader from re-attaching.
                    pass

        if _log_reader_state["stop"]:
            break

        # The container may have stopped or restarted, and `docker logs -f`
        # exits when it does. Pause briefly, then re-attach, so the server
        # coming back up resumes the stream without anyone intervening.
        server.socketio.sleep(2)

    with _log_streams_lock:
        _log_reader_state["running"] = False


def ensure_log_reader():
    """Start the single follower thread if it is not already running"""
    with _log_streams_lock:
        if _log_reader_state["running"]:
            return
        _log_reader_state["running"] = True
        _log_reader_state["stop"] = False
    server.socketio.start_background_task(_log_reader)


def stop_log_reader():
    """Stop the follower.

    Setting the flag alone is not enough. A quiet server leaves the reader
    blocked in `for line in proc.stdout`, where it never gets to check the
    flag, so `docker logs -f` is killed to break the read. The reader then
    unblocks, sees the flag and exits.
    """
    with _log_streams_lock:
        _log_reader_state["stop"] = True
        proc = _log_reader_state["proc"]

    if proc is not None:
        try:
            proc.kill()
        except OSError:
            # Already exited, which is the outcome we wanted anyway.
            pass


@_on("connect")
def handle_connect(auth):
    """Handle WebSocket connection.

    Accepts either an API key or a JWT, mirroring auth_guard.require_auth's REST
    behavior — without the token path, any user who logged in with a
    username/password (no API key ever issued) could use every REST
    endpoint but not the log/console stream.
    """
    api_key = auth.get("api_key") if auth else None
    token = auth.get("token") if auth else None

    identity = None  # ("api_key", key) or ("user", username)

    if api_key:
        if api_key not in server.API_KEYS:
            server.socketio.emit("error", {"message": "Invalid API key"}, room=request.sid)
            disconnect(request.sid)
            return False

        key_info = server.API_KEYS.get(api_key, {})
        if not key_info.get("enabled", True):
            server.socketio.emit("error", {"message": "API key disabled"}, room=request.sid)
            disconnect(request.sid)
            return False

        identity = ("api_key", api_key)
    elif token:
        username = auth_crypto.verify_token(token)
        if not username or username not in server.USERS:
            server.socketio.emit("error", {"message": "Invalid or expired token"}, room=request.sid)
            disconnect(request.sid)
            return False

        if not server.USERS[username].get("enabled", True):
            server.socketio.emit("error", {"message": "Account disabled"}, room=request.sid)
            disconnect(request.sid)
            return False

        identity = ("user", username)
    else:
        server.socketio.emit("error", {"message": "API key or token required"}, room=request.sid)
        disconnect(request.sid)
        return False

    # The log stream is server output, so it needs the same permission the
    # REST log endpoints require. Any enabled key used to be enough.
    if not _identity_has_permission(identity, "logs.view"):
        server.socketio.emit("error", {"message": "Permission denied: logs.view"}, room=request.sid)
        disconnect(request.sid)
        return False

    with _log_streams_lock:
        active_log_streams.add(request.sid)
        _stream_keys[request.sid] = identity

    # Send the backlog to this client only, then let the shared follower
    # deliver everything that arrives afterwards.
    server.socketio.emit("logs", {"logs": get_log_tail(LOG_BACKLOG_LINES), "type": "initial"}, room=request.sid)
    server.socketio.emit("connected", {"message": "Connected to log stream"}, room=request.sid)

    ensure_log_reader()
    return True  # connection accepted


@_on("disconnect")
def handle_disconnect():
    """Handle WebSocket disconnection"""
    with _log_streams_lock:
        active_log_streams.discard(request.sid)
        _stream_keys.pop(request.sid, None)


def _identity_has_permission(identity, permission):
    """Resolve a stream identity from handle_connect to a live permission check."""
    if not identity:
        return False
    kind, value = identity
    if kind == "api_key":
        key_info = server.API_KEYS.get(value)
        if not key_info or not key_info.get("enabled", True):
            return False
        return permission in rbac.get_api_key_permissions(key_info)
    if kind == "user":
        if value not in server.USERS or not server.USERS[value].get("enabled", True):
            return False
        return auth_guard.has_permission(value, permission)
    return False


def _stream_may(permission):
    """Check the live scope of the identity that opened this connection.

    Re-read rather than trusting what the key or user could do at connect
    time: a key revoked, a user disabled, or a role narrowed through the
    management API would otherwise keep its old rights on an open socket
    for as long as it stayed connected.
    """
    with _log_streams_lock:
        identity = _stream_keys.get(request.sid)

    return _identity_has_permission(identity, permission)


def _stream_actor():
    """Who opened this socket, named as auth_guard.get_username_from_request() names
    REST callers, for the audit log. Commands sent over the socket were all
    recorded as "__api_key__", whoever sent them."""
    with _log_streams_lock:
        identity = _stream_keys.get(request.sid)
    if not identity:
        return "unknown"
    kind, value = identity
    if kind == "api_key":
        return f"api_key:{server.API_KEYS.get(value, {}).get('name', 'unknown')}"
    return value


@_on("request_logs")
def handle_request_logs(data):
    """Handle log request from client"""
    if not _stream_may("logs.view"):
        server.socketio.emit("error", {"message": "Permission denied: logs.view"}, room=request.sid)
        return
    lines = data.get("lines", 100) if data else 100
    logs = get_log_tail(lines)
    server.socketio.emit("logs", {"logs": logs, "type": "request"}, room=request.sid)


@_on("execute_command")
def handle_execute_command(data):
    """Handle command execution from client"""
    # The connect handler only proved the key was valid, never that it was
    # allowed to run commands, so a read-only key could drive the console.
    if not _stream_may("server.command"):
        server.socketio.emit("command_error", {"message": "Permission denied: server.command"}, room=request.sid)
        return

    command = data.get("command") if data else None
    if not command:
        server.socketio.emit("command_error", {"message": "Command required"}, room=request.sid)
        return
    if not isinstance(command, str):
        # Raising inside the sanitizer happens before the try block below,
        # which would leave the client waiting with no error at all.
        server.socketio.emit("command_error", {"message": "Command must be a string"}, room=request.sid)
        return

    # Sanitise exactly as POST /api/server/command does. This path reached
    # RCON unvalidated, so the WebSocket was a way around the command
    # allowlist that the REST endpoint enforces.
    is_valid, sanitized_command, _ = sanitize_minecraft_command(command)
    if not is_valid:
        server.log_audit_event(
            _stream_actor(),
            "server.command.rejected",
            {"original_command": sanitize_string(command[:100]), "source": "websocket"},
        )
        server.socketio.emit("command_error", {"message": "Invalid command format"}, room=request.sid)
        return
    command = sanitized_command

    server.log_audit_event(_stream_actor(), "server.command", {"command": sanitize_string(command[:100])})

    # Execute command via RCON
    try:
        stdout, stderr, code = server.run_rcon_command(command)
        if code == 0:
            server.socketio.emit(
                "command_response", {"command": command, "response": stdout, "success": True}, room=request.sid
            )
        else:
            server.socketio.emit(
                "command_response",
                {"command": command, "response": stderr or "Command failed", "success": False},
                room=request.sid,
            )
    except Exception as e:  # noqa: BLE001 - socket handler boundary: logged, generic error to the client
        server.app.logger.error(f"Failed to execute command over the socket: {e}")
        server.socketio.emit(
            "command_error",
            {"message": "Failed to execute command", "command": command},
            room=request.sid,
        )
