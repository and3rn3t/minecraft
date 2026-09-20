#!/usr/bin/env python3
"""Game event bus: turns Minecraft log lines into typed, persisted events.

The API already follows the container log to stream raw text to the browser.
That stream is the only real-time signal the server produces, but as raw text it
can only be displayed, not acted on. This module parses each line into a typed
event, appends it to a daily JSONL file, and hands it to any registered handler.

Everything reactive builds on this: death messages, join notifications,
chat-triggered features, statistics that do not depend on re-reading the whole
log. Statistics that Minecraft itself keeps are read from its own files by
``api/player_stats.py``; events recorded here cover what the game does not
count, and each is recorded exactly once.

Writes are buffered. The Pi runs from an SD card with finite write endurance, so
a continuous stream of one-line appends is flushed in batches rather than per
event.
"""

from __future__ import annotations

import json
import os
import re
import threading
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Iterator, Optional

PROJECT_ROOT = Path(__file__).parent.parent


def _resolve_events_dir() -> Path:
    """Where the daily JSONL files live.

    Defaults to ``data/events`` inside the project. The Pi boots from an SD
    card, and this is the one directory the server writes to continuously, so
    when an SSD is attached it is the thing worth moving: set ``MC_EVENTS_DIR``
    to a path on it. Batching and the 30-day prune already limit how much is
    written; moving the directory takes the writes off the card altogether.
    """
    configured = os.environ.get("MC_EVENTS_DIR", "").strip()
    if configured:
        return Path(configured).expanduser()
    return PROJECT_ROOT / "data" / "events"


EVENTS_DIR = _resolve_events_dir()

# Event type constants. Kept as plain strings so they serialise directly.
EVENT_CHAT = "chat"
EVENT_CONNECT = "connect"
EVENT_JOIN = "join"
EVENT_LEAVE = "leave"
EVENT_DEATH = "death"
EVENT_ADVANCEMENT = "advancement"
EVENT_COMMAND = "command"
EVENT_SERVER_READY = "server_ready"
EVENT_SERVER_STOPPING = "server_stopping"

ALL_EVENT_TYPES = (
    EVENT_CHAT,
    EVENT_CONNECT,
    EVENT_JOIN,
    EVENT_LEAVE,
    EVENT_DEATH,
    EVENT_ADVANCEMENT,
    EVENT_COMMAND,
    EVENT_SERVER_READY,
    EVENT_SERVER_STOPPING,
)

# Flush after this many buffered events, or this many seconds, whichever first.
FLUSH_EVERY_EVENTS = 20
FLUSH_EVERY_SECONDS = 30.0
# Daily files older than this are pruned, again to protect the SD card. With
# the events directory moved to an SSD there is no card to protect, so this is
# worth raising: set MC_EVENTS_RETENTION_DAYS. A history worth keeping is the
# point of recording events at all, and the Gazette and the leaderboards read
# from it.
def _resolve_retention_days(default: int = 30) -> int:
    configured = os.environ.get("MC_EVENTS_RETENTION_DAYS", "").strip()
    if not configured:
        return default
    try:
        days = int(configured)
    except ValueError:
        return default
    # Zero or negative disables pruning, which prune() already understands.
    return days


DEFAULT_RETENTION_DAYS = _resolve_retention_days()

# Minecraft usernames: 3-16 characters of word characters.
_NAME = r"[A-Za-z0-9_]{3,16}"

# Strips the log prefix: "[16:04:23] [Server thread/INFO]: message".
# Paper and Fabric use other thread names, so the thread field is matched loosely.
_LINE_RE = re.compile(r"^\[(?P<time>\d{2}:\d{2}:\d{2})\]\s*\[(?P<thread>[^\]]+)\]:\s*(?P<message>.*)$")

_CHAT_RE = re.compile(rf"^<(?P<player>{_NAME})>\s?(?P<message>.*)$")
_JOIN_RE = re.compile(rf"^(?P<player>{_NAME}) joined the game$")
_LEAVE_RE = re.compile(rf"^(?P<player>{_NAME}) left the game$")
_COMMAND_RE = re.compile(rf"^(?P<player>{_NAME}) issued server command: (?P<command>.+)$")
_ADVANCEMENT_RE = re.compile(
    rf"^(?P<player>{_NAME}) has (?:made the advancement|completed the challenge|reached the goal) "
    r"\[(?P<advancement>[^\]]+)\]$"
)
_LOGIN_RE = re.compile(rf"^(?P<player>{_NAME})\[/(?P<address>[^\]]+)\] logged in with entity id")
_READY_RE = re.compile(r'^Done \((?P<startup>[^)]+)\)! For help, type "help"$')
_STOPPING_RE = re.compile(r"^Stopping (?:the )?server$")

# Vanilla death messages have no marker of their own; they are a bare sentence
# beginning with the player's name. These are the opening phrases of the
# death.attack.* strings in 1.20.4. Anything not matched here is simply not
# treated as a death, which is the safe direction to fail.
_DEATH_PHRASES = (
    r"was shot by",
    r"was pummeled by",
    r"was pricked to death",
    r"walked into a cactus while trying to escape",
    r"drowned",
    r"died from dehydration",
    r"died",
    r"experienced kinetic energy",
    r"blew up",
    r"was blown up by",
    r"was killed by",
    r"hit the ground too hard",
    r"fell from a high place",
    r"fell off (?:a ladder|some vines|some weeping vines|some twisting vines|scaffolding)",
    r"fell while climbing",
    r"was impaled on a stalagmite",
    r"was squashed by",
    r"was skewered by a falling stalactite",
    r"went up in flames",
    r"burned to death",
    r"was burnt to a crisp while fighting",
    r"went off with a bang",
    r"tried to swim in lava",
    r"was struck by lightning",
    r"discovered the floor was lava",
    r"walked into the danger zone",
    r"froze to death",
    r"was frozen to death by",
    r"was slain by",
    r"was fireballed by",
    r"was stung to death",
    r"was shot by a skull from",
    r"starved to death",
    r"suffocated in a wall",
    r"was squished too much",
    r"was poked to death by a sweet berry bush",
    r"was killed trying to hurt",
    r"was impaled by",
    r"fell out of the world",
    r"didn't want to live in the same world as",
    r"withered away",
    r"was roared at by",
    r"was obliterated by a sonically-charged shriek",
    r"left the confines of this world",
    r"got finished off by",
    r"was doomed to fall",
    r"was stung to death by",
)
_DEATH_RE = re.compile(rf"^(?P<player>{_NAME}) (?P<cause>(?:{'|'.join(_DEATH_PHRASES)})\b.*)$")


@dataclass(frozen=True)
class GameEvent:
    """One thing that happened on the server.

    ``timestamp`` is when the line was ingested, in UTC. The server's own clock
    reading is kept in ``data["log_time"]``: log lines carry only ``HH:MM:SS``
    with no date, so deriving a full timestamp from them breaks across midnight.
    """

    type: str
    timestamp: str
    player: Optional[str] = None
    data: dict = field(default_factory=dict)
    raw: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), separators=(",", ":"))


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_line(line: str) -> Optional[GameEvent]:
    """Parse one server log line into a :class:`GameEvent`, or ``None``.

    Returning ``None`` for the overwhelming majority of lines is the expected
    case; most of a Minecraft log is startup noise and chunk bookkeeping.
    """
    if not line:
        return None

    match = _LINE_RE.match(line.strip())
    if not match:
        return None

    log_time = match.group("time")
    message = match.group("message").strip()
    if not message:
        return None

    base = {"log_time": log_time}

    # Chat is checked first and deliberately. A player can type anything,
    # including a sentence that looks exactly like a death message, so the
    # "<name> " form has to win before any other pattern is tried.
    chat = _CHAT_RE.match(message)
    if chat:
        return GameEvent(
            type=EVENT_CHAT,
            timestamp=_now_iso(),
            player=chat.group("player"),
            data={**base, "message": chat.group("message")},
            raw=line,
        )

    join = _JOIN_RE.match(message)
    if join:
        return GameEvent(EVENT_JOIN, _now_iso(), join.group("player"), dict(base), line)

    leave = _LEAVE_RE.match(message)
    if leave:
        return GameEvent(EVENT_LEAVE, _now_iso(), leave.group("player"), dict(base), line)

    advancement = _ADVANCEMENT_RE.match(message)
    if advancement:
        return GameEvent(
            type=EVENT_ADVANCEMENT,
            timestamp=_now_iso(),
            player=advancement.group("player"),
            data={**base, "advancement": advancement.group("advancement")},
            raw=line,
        )

    command = _COMMAND_RE.match(message)
    if command:
        return GameEvent(
            type=EVENT_COMMAND,
            timestamp=_now_iso(),
            player=command.group("player"),
            data={**base, "command": command.group("command")},
            raw=line,
        )

    login = _LOGIN_RE.match(message)
    if login:
        # A player session produces two lines: this one, carrying the network
        # address, and "joined the game" a moment later. They are separate types
        # so that counting joins does not double-count every session. The
        # address is recorded but not surfaced anywhere by default; it is here so
        # a future "a new device connected" alert can use it.
        return GameEvent(
            type=EVENT_CONNECT,
            timestamp=_now_iso(),
            player=login.group("player"),
            data={**base, "address": login.group("address")},
            raw=line,
        )

    death = _DEATH_RE.match(message)
    if death:
        return GameEvent(
            type=EVENT_DEATH,
            timestamp=_now_iso(),
            player=death.group("player"),
            data={**base, "cause": death.group("cause"), "message": message},
            raw=line,
        )

    ready = _READY_RE.match(message)
    if ready:
        return GameEvent(
            type=EVENT_SERVER_READY,
            timestamp=_now_iso(),
            data={**base, "startup_time": ready.group("startup")},
            raw=line,
        )

    if _STOPPING_RE.match(message):
        return GameEvent(EVENT_SERVER_STOPPING, _now_iso(), None, dict(base), line)

    return None


class EventBus:
    """Parses, persists and dispatches game events.

    Handlers are called synchronously in registration order. A handler that
    raises is logged and skipped rather than being allowed to take down the
    reader thread that feeds the bus.
    """

    def __init__(
        self,
        events_dir: Optional[Path] = None,
        retention_days: int = DEFAULT_RETENTION_DAYS,
        flush_every_events: int = FLUSH_EVERY_EVENTS,
        flush_every_seconds: float = FLUSH_EVERY_SECONDS,
    ) -> None:
        self.events_dir = events_dir if events_dir is not None else EVENTS_DIR
        self.retention_days = retention_days
        self.flush_every_events = flush_every_events
        self.flush_every_seconds = flush_every_seconds

        self._handlers: list[Callable[[GameEvent], None]] = []
        self._buffer: list[GameEvent] = []
        self._lock = threading.RLock()
        # Separate from _lock: the buffer swap is quick, but the file append
        # must not interleave with another flush, and holding _lock across the
        # write would block every publish for the duration of the I/O.
        self._write_lock = threading.Lock()
        self._last_flush = datetime.now(timezone.utc)
        self._last_pruned_date: Optional[str] = None
        self._error_logger: Optional[Callable[[str], None]] = None
        self._flush_timer: Optional[threading.Timer] = None

    def set_error_logger(self, logger: Callable[[str], None]) -> None:
        """Route handler errors somewhere visible, normally ``app.logger``."""
        self._error_logger = logger

    def _log_error(self, message: str) -> None:
        if self._error_logger is not None:
            try:
                self._error_logger(message)
            except Exception:  # noqa: BLE001 - logging must never raise
                # The error logger is supplied by the caller and may itself be
                # broken or closed. Swallowing it here is deliberate: a failure
                # to report a problem must not become a second problem on the
                # thread that feeds the bus.
                pass

    def subscribe(self, handler: Callable[[GameEvent], None]) -> Callable[[GameEvent], None]:
        """Register a handler. Returns it, so it can be used as a decorator."""
        with self._lock:
            if handler not in self._handlers:
                self._handlers.append(handler)
        return handler

    def unsubscribe(self, handler: Callable[[GameEvent], None]) -> None:
        with self._lock:
            if handler in self._handlers:
                self._handlers.remove(handler)

    @property
    def handler_count(self) -> int:
        with self._lock:
            return len(self._handlers)

    def handle_line(self, line: str) -> Optional[GameEvent]:
        """Parse a log line and publish it if it is an event."""
        event = parse_line(line)
        if event is not None:
            self.publish(event)
        return event

    def publish(self, event: GameEvent) -> None:
        """Persist an event and hand it to every handler."""
        with self._lock:
            self._buffer.append(event)
            handlers = list(self._handlers)
            should_flush = len(self._buffer) >= self.flush_every_events or (
                (datetime.now(timezone.utc) - self._last_flush).total_seconds() >= self.flush_every_seconds
            )

        if should_flush:
            self.flush()

        for handler in handlers:
            try:
                handler(event)
            except Exception as exc:  # noqa: BLE001 - one bad handler must not stop the rest
                self._log_error(f"Event handler {getattr(handler, '__name__', handler)!r} failed: {exc}")

    def flush(self) -> int:
        """Write buffered events to today's file. Returns the number written."""
        with self._lock:
            if not self._buffer:
                self._last_flush = datetime.now(timezone.utc)
                return 0
            pending, self._buffer = self._buffer, []
            self._last_flush = datetime.now(timezone.utc)

        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        try:
            with self._write_lock:
                self.events_dir.mkdir(parents=True, exist_ok=True)
                target = self.events_dir / f"{today}.jsonl"
                with open(target, "a", encoding="utf-8") as handle:
                    for event in pending:
                        handle.write(event.to_json() + "\n")
        except OSError as exc:
            # Losing an event to a full or read-only disk must not stop the
            # server from running, so this is reported and dropped.
            self._log_error(f"Could not persist {len(pending)} event(s): {exc}")
            return 0

        if self._last_pruned_date != today:
            self._last_pruned_date = today
            self.prune()

        return len(pending)

    def start_periodic_flush(self) -> None:
        """Flush on a timer as well as on publish.

        The size and age thresholds are only evaluated when something is
        published, so on a quiet server the last few events would sit in memory
        until the next one arrived, and be lost if the process stopped first.
        A daemon timer bounds that window to ``flush_every_seconds``.
        """
        with self._lock:
            if self._flush_timer is not None:
                return
            self._schedule_flush_locked()

    def stop_periodic_flush(self) -> None:
        """Cancel the flush timer and write out anything still buffered."""
        with self._lock:
            timer, self._flush_timer = self._flush_timer, None
        if timer is not None:
            timer.cancel()
        self.flush()

    def _schedule_flush_locked(self) -> None:
        """Arm the next timer tick. Caller holds ``_lock``."""
        timer = threading.Timer(self.flush_every_seconds, self._periodic_flush)
        timer.daemon = True
        self._flush_timer = timer
        timer.start()

    def _periodic_flush(self) -> None:
        try:
            self.flush()
        except Exception as exc:  # noqa: BLE001 - a timer thread must not die
            self._log_error(f"Periodic flush failed: {exc}")
        finally:
            with self._lock:
                if self._flush_timer is not None:
                    self._schedule_flush_locked()

    def prune(self) -> int:
        """Delete daily files older than the retention window."""
        if self.retention_days <= 0 or not self.events_dir.exists():
            return 0

        cutoff = (datetime.now(timezone.utc) - timedelta(days=self.retention_days)).date()
        removed = 0
        for path in self.events_dir.glob("*.jsonl"):
            try:
                file_date = datetime.strptime(path.stem, "%Y-%m-%d").date()
            except ValueError:
                continue
            if file_date < cutoff:
                try:
                    path.unlink()
                    removed += 1
                except OSError:
                    continue
        return removed

    def read(self, limit: int = 100, event_type: Optional[str] = None, player: Optional[str] = None) -> list[dict]:
        """Return the most recent stored events, newest first.

        Buffered events are flushed first so a caller never sees a stale view of
        what just happened.
        """
        self.flush()

        collected: list[dict] = []
        for path in sorted(self.events_dir.glob("*.jsonl"), reverse=True) if self.events_dir.exists() else []:
            for record in _read_jsonl_reversed(path):
                if event_type and record.get("type") != event_type:
                    continue
                if player and record.get("player") != player:
                    continue
                collected.append(record)
                if len(collected) >= limit:
                    return collected
        return collected


def _read_jsonl_reversed(path: Path) -> Iterator[dict]:
    """Yield the records of a JSONL file newest first.

    Daily event files stay small enough to read whole; a busy day on a family
    server is measured in thousands of lines, not millions.
    """
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return
    for line in reversed(lines):
        line = line.strip()
        if not line:
            continue
        try:
            yield json.loads(line)
        except json.JSONDecodeError:
            # A torn final line from an interrupted write; skip it.
            continue


# Shared bus, created on first use.
_bus: Optional[EventBus] = None
_bus_lock = threading.Lock()


def get_bus() -> EventBus:
    """Return the process-wide event bus."""
    global _bus
    with _bus_lock:
        if _bus is None:
            _bus = EventBus()
        return _bus


def reset_bus() -> None:
    """Drop the shared bus. Used by tests."""
    global _bus
    with _bus_lock:
        if _bus is not None:
            _bus.stop_periodic_flush()
        _bus = None
