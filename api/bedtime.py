#!/usr/bin/env python3
"""Bedtime mode: a scheduled, warned, enforceable end to the evening.

A shutdown that arrives without warning starts an argument. This gives a
countdown instead: a bossbar that fills up, titles at the agreed marks, and a
goodnight message. The end of the evening becomes something the server
announced rather than something a parent did.

It also holds. Stopping the server is not enough on its own, because anything
that brings the container back, a restart policy or an update timer, reopens
the evening. So bedtime defines a closed window rather than a single moment:
between bedtime and the wake time, anyone who joins is sent straight back out
with a message saying when the server opens again.

All the scheduling logic takes the current time as an argument so it can be
tested without waiting for the evening. The thread in :meth:`Bedtime.start`
supplies the real clock.
"""

from __future__ import annotations

import queue
import threading
import time as time_module
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Callable, Optional

PROJECT_ROOT = Path(__file__).parent.parent
BEDTIME_CONFIG_FILE = PROJECT_ROOT / "config" / "bedtime.conf"

# What happens when the countdown reaches zero.
ACTION_STOP = "stop"
ACTION_KICK = "kick"
ACTION_ANNOUNCE = "announce"
VALID_ACTIONS = (ACTION_STOP, ACTION_KICK, ACTION_ANNOUNCE)

WEEKDAY_NAMES = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")

DEFAULT_WEEKNIGHT = time(20, 30)
DEFAULT_WEEKEND = time(21, 30)
DEFAULT_WAKE = time(7, 0)
# Friday and Saturday nights are the late ones: it is the night before a
# non-school morning that matters, not the day itself.
DEFAULT_WEEKEND_NIGHTS = ("friday", "saturday")
DEFAULT_WARN_MINUTES = (30, 15, 10, 5, 1)
DEFAULT_EXTEND_MINUTES = 15
DEFAULT_MAX_EXTENSIONS = 1

BOSSBAR_ID = "minecraft:bedtime"
# How often the thread re-evaluates. Fine enough for a smooth bossbar without
# putting a meaningful load on a Pi.
TICK_SECONDS = 5.0


def parse_clock(value: str, fallback: time) -> time:
    """Parse ``HH:MM`` into a :class:`~datetime.time`, falling back on nonsense."""
    try:
        hour, minute = value.strip().split(":", 1)
        return time(int(hour), int(minute))
    except (AttributeError, ValueError):
        return fallback


@dataclass
class BedtimeConfig:
    """When bedtime is, how it is announced, and what it does."""

    enabled: bool = False
    weeknight: time = DEFAULT_WEEKNIGHT
    weekend: time = DEFAULT_WEEKEND
    wake: time = DEFAULT_WAKE
    weekend_nights: tuple[str, ...] = DEFAULT_WEEKEND_NIGHTS
    warn_minutes: tuple[int, ...] = DEFAULT_WARN_MINUTES
    extend_minutes: int = DEFAULT_EXTEND_MINUTES
    max_extensions: int = DEFAULT_MAX_EXTENSIONS
    action: str = ACTION_STOP
    bossbar: bool = True

    def bedtime_for(self, day: date) -> time:
        """The bedtime that applies to the evening of ``day``."""
        return self.weekend if WEEKDAY_NAMES[day.weekday()] in self.weekend_nights else self.weeknight


def load_bedtime_config(config_file: Optional[Path] = None) -> BedtimeConfig:
    """Read ``config/bedtime.conf``.

    Bedtime is **disabled unless the file says otherwise**. A feature that can
    stop the server and turn people away should never switch itself on because
    a default said so.
    """
    path = config_file if config_file is not None else BEDTIME_CONFIG_FILE
    config = BedtimeConfig()

    if not path.exists():
        return config

    try:
        content = path.read_text(encoding="utf-8")
    except OSError:
        return config

    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("\"'")

        if key == "ENABLED":
            config.enabled = value.lower() in ("1", "true", "yes", "on")
        elif key == "WEEKNIGHT_BEDTIME":
            config.weeknight = parse_clock(value, DEFAULT_WEEKNIGHT)
        elif key == "WEEKEND_BEDTIME":
            config.weekend = parse_clock(value, DEFAULT_WEEKEND)
        elif key == "WAKE_TIME":
            config.wake = parse_clock(value, DEFAULT_WAKE)
        elif key == "WEEKEND_NIGHTS":
            nights = tuple(n.strip().lower() for n in value.split(",") if n.strip().lower() in WEEKDAY_NAMES)
            config.weekend_nights = nights
        elif key == "WARN_MINUTES":
            minutes = []
            for part in value.split(","):
                try:
                    minutes.append(int(part.strip()))
                except ValueError:
                    continue
            if minutes:
                config.warn_minutes = tuple(sorted({m for m in minutes if m > 0}, reverse=True))
        elif key == "EXTEND_MINUTES":
            try:
                config.extend_minutes = max(0, int(value))
            except ValueError:
                # A typo here must not stop the server starting. The default
                # stands and bedtime still works, which beats refusing to boot.
                pass
        elif key == "MAX_EXTENSIONS":
            try:
                config.max_extensions = max(0, int(value))
            except ValueError:
                # As above: keep the default rather than fail on a bad value.
                pass
        elif key == "ACTION" and value.lower() in VALID_ACTIONS:
            config.action = value.lower()
        elif key == "BOSSBAR":
            config.bossbar = value.lower() in ("1", "true", "yes", "on")

    return config


@dataclass
class _NightState:
    """What has already happened tonight.

    Keyed by the date of the evening, so everything resets by itself when the
    next one comes round rather than needing to be cleared.
    """

    night: Optional[date] = None
    extensions: int = 0
    extra_minutes: int = 0
    skipped: bool = False
    warned: set = field(default_factory=set)
    enforced: bool = False

    def reset_to(self, night: date) -> None:
        self.night = night
        self.extensions = 0
        self.extra_minutes = 0
        self.skipped = False
        self.warned = set()
        self.enforced = False


class Bedtime:
    """Runs the countdown and enforces the closed window."""

    def __init__(
        self,
        config: Optional[BedtimeConfig] = None,
        runner: Optional[Callable[[str], None]] = None,
        stopper: Optional[Callable[[], None]] = None,
    ) -> None:
        self.config = config or BedtimeConfig()
        # Injected rather than imported so the whole class is testable without
        # a server, RCON or Docker.
        self.runner = runner
        self.stopper = stopper

        self._state = _NightState()
        self._lock = threading.RLock()
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._error_logger: Optional[Callable[[str], None]] = None
        self._bossbar_shown = False
        # Commands raised from other threads, chiefly the event bus. See
        # on_player_join for why they cannot be sent where they are raised.
        self._actions: queue.Queue = queue.Queue()

    def set_error_logger(self, logger: Callable[[str], None]) -> None:
        self._error_logger = logger

    def _log_error(self, message: str) -> None:
        if self._error_logger is not None:
            try:
                self._error_logger(message)
            except Exception:  # noqa: BLE001 - reporting a failure must not fail
                # Supplied by the caller and possibly closed. Losing the report
                # beats raising on the timer thread.
                pass

    def _run(self, command: str) -> bool:
        """Send one command, reporting rather than raising on failure."""
        if self.runner is None:
            return False
        try:
            self.runner(command)
            return True
        except Exception as exc:  # noqa: BLE001 - the server may be down
            self._log_error(f"Bedtime command failed ({command.split()[0]}): {exc}")
            return False

    # Scheduling

    def _night_of(self, moment: datetime) -> date:
        """Which evening a moment belongs to.

        Anything before the wake time belongs to the previous evening, so that
        01:00 on Saturday is still Friday night.
        """
        if moment.time() < self.config.wake:
            return (moment - timedelta(days=1)).date()
        return moment.date()

    def _base_bedtime(self, night: date) -> datetime:
        """Tonight's bedtime before any extension."""
        return datetime.combine(night, self.config.bedtime_for(night))

    def bedtime_on(self, night: date) -> datetime:
        """Tonight's bedtime, including any extension granted tonight."""
        base = self._base_bedtime(night)
        with self._lock:
            if self._state.night == night:
                return base + timedelta(minutes=self._state.extra_minutes)
        return base

    def wake_after(self, night: date) -> datetime:
        """When the server opens again after ``night``."""
        bedtime = self._base_bedtime(night)
        wake = datetime.combine(night, self.config.wake)
        if wake <= bedtime:
            wake += timedelta(days=1)
        return wake

    def next_bedtime(self, now: datetime) -> datetime:
        """The next bedtime that will actually be enforced."""
        night = self._night_of(now)
        candidate = self.bedtime_on(night)
        if now < candidate and not self.is_skipped(night):
            return candidate

        # Tonight has passed or been skipped; look at following evenings.
        following = night + timedelta(days=1)
        for _ in range(8):
            if not self.is_skipped(following):
                return self._base_bedtime(following)
            following += timedelta(days=1)
        return self._base_bedtime(following)

    def is_skipped(self, night: date) -> bool:
        with self._lock:
            return self._state.night == night and self._state.skipped

    def is_closed(self, now: datetime) -> bool:
        """Whether the server is inside a bedtime window right now."""
        if not self.config.enabled:
            return False

        night = self._night_of(now)
        if self.is_skipped(night):
            return False
        return self.bedtime_on(night) <= now < self.wake_after(night)

    def seconds_until_bedtime(self, now: datetime) -> Optional[float]:
        """Seconds remaining, or ``None`` when the window is already closed."""
        if self.is_closed(now):
            return None
        return (self.next_bedtime(now) - now).total_seconds()

    # Controls

    def extend(self, now: Optional[datetime] = None) -> tuple[bool, str]:
        """Grant "five more minutes", within the configured limit."""
        now = now or datetime.now()
        night = self._night_of(now)

        with self._lock:
            self._ensure_night(night)
            if self.config.max_extensions <= 0:
                return False, "Extensions are disabled"
            if self._state.extensions >= self.config.max_extensions:
                return False, "No extensions left tonight"
            if self._state.enforced:
                return False, "Bedtime has already happened tonight"

            self._state.extensions += 1
            self._state.extra_minutes += self.config.extend_minutes
            minutes = self.config.extend_minutes
            # A warning already given no longer applies to the new deadline.
            self._state.warned = set()

        self._announce(f"Bedtime extended by {minutes} minutes. Make them count.")
        return True, f"Extended by {minutes} minutes"

    def skip_tonight(self, now: Optional[datetime] = None) -> tuple[bool, str]:
        """Cancel bedtime for this evening only."""
        now = now or datetime.now()
        night = self._night_of(now)

        with self._lock:
            self._ensure_night(night)
            if self._state.enforced:
                return False, "Bedtime has already happened tonight"
            self._state.skipped = True

        self._clear_bossbar()
        self._announce("No bedtime tonight. Enjoy it.")
        return True, "Bedtime skipped for tonight"

    def start_now(self, now: Optional[datetime] = None) -> tuple[bool, str]:
        """Bring bedtime forward to right now."""
        now = now or datetime.now()
        night = self._night_of(now)

        with self._lock:
            self._ensure_night(night)
            if self._state.enforced:
                return False, "Bedtime has already happened tonight"

        self._enforce(now)
        return True, "Bedtime started"

    def _ensure_night(self, night: date) -> None:
        """Roll state over to a new evening. Caller holds the lock."""
        if self._state.night != night:
            self._state.reset_to(night)

    # The countdown

    def status(self, now: Optional[datetime] = None) -> dict:
        """Everything a dashboard or a phone widget needs, in one shape."""
        now = now or datetime.now()
        night = self._night_of(now)
        closed = self.is_closed(now)
        remaining = self.seconds_until_bedtime(now)

        with self._lock:
            extensions_used = self._state.extensions if self._state.night == night else 0
            skipped = self._state.night == night and self._state.skipped

        return {
            "enabled": self.config.enabled,
            "closed": closed,
            "skipped_tonight": skipped,
            "next_bedtime": self.next_bedtime(now).isoformat(timespec="minutes"),
            "seconds_until_bedtime": None if remaining is None else max(0, int(remaining)),
            "opens_at": self.wake_after(night).isoformat(timespec="minutes") if closed else None,
            "extensions_used": extensions_used,
            "extensions_allowed": self.config.max_extensions,
            "extend_minutes": self.config.extend_minutes,
            "action": self.config.action,
            "weeknight_bedtime": self.config.weeknight.strftime("%H:%M"),
            "weekend_bedtime": self.config.weekend.strftime("%H:%M"),
            "wake_time": self.config.wake.strftime("%H:%M"),
        }

    def tick(self, now: Optional[datetime] = None) -> None:
        """One evaluation of the clock. Safe to call as often as you like."""
        if not self.config.enabled:
            return

        now = now or datetime.now()
        night = self._night_of(now)

        with self._lock:
            self._ensure_night(night)
            if self._state.skipped:
                return
            already_enforced = self._state.enforced

        bedtime = self.bedtime_on(night)
        remaining = (bedtime - now).total_seconds()

        if remaining <= 0:
            if not already_enforced:
                self._enforce(now)
            return

        self._warn_if_due(remaining)
        self._update_bossbar(remaining)

    def _warn_if_due(self, remaining_seconds: float) -> None:
        """Fire the warning that describes the time actually left.

        Every mark at or above the remaining time is due, and the one worth
        saying is the smallest of them. Announcing the largest instead would
        mean a server started with ten minutes to go greeting everyone with
        "30 minutes until bedtime".

        All the due marks are recorded as given, so the larger ones do not fire
        afterwards once they no longer describe anything.
        """
        remaining_minutes = remaining_seconds / 60.0
        due = [mark for mark in self.config.warn_minutes if remaining_minutes <= mark]
        if not due:
            return

        with self._lock:
            if all(mark in self._state.warned for mark in due):
                return
            self._state.warned.update(due)

        mark = min(due)
        unit = "minute" if mark == 1 else "minutes"
        self._title(f"{mark} {unit} until bedtime")

    def _update_bossbar(self, remaining_seconds: float) -> None:
        """Show a bar that empties as bedtime approaches.

        Only shown inside the first warning mark, so it is not sitting on the
        screen all afternoon.
        """
        if not self.config.bossbar or not self.config.warn_minutes:
            return

        window_seconds = max(self.config.warn_minutes) * 60
        if remaining_seconds > window_seconds:
            self._clear_bossbar()
            return

        if not self._bossbar_shown:
            self._run(f'bossbar add {BOSSBAR_ID} {{"text":"Bedtime"}}')
            self._run(f"bossbar set {BOSSBAR_ID} color red")
            self._run(f"bossbar set {BOSSBAR_ID} max {int(window_seconds)}")
            self._run(f"bossbar set {BOSSBAR_ID} players @a")
            self._bossbar_shown = True

        minutes_left = max(0, int(remaining_seconds // 60))
        label = f"Bedtime in {minutes_left} min" if minutes_left else "Bedtime now"
        self._run(f'bossbar set {BOSSBAR_ID} name {{"text":"{label}"}}')
        self._run(f"bossbar set {BOSSBAR_ID} value {max(0, int(remaining_seconds))}")

    def _clear_bossbar(self) -> None:
        if self._bossbar_shown:
            self._run(f"bossbar remove {BOSSBAR_ID}")
            self._bossbar_shown = False

    def _enforce(self, now: datetime) -> None:
        """Bedtime has arrived. Say goodnight, then do what was configured.

        Idempotent, and it has to be. The bedtime thread reaches this from
        tick(), and an API request can reach it from start_now() at the same
        moment. Both of those check `enforced` before calling, so without an
        atomic check-and-set here the evening could be closed twice: two
        goodnights, two kicks, two attempts to stop the server.
        """
        with self._lock:
            self._ensure_night(self._night_of(now))
            if self._state.enforced:
                return
            self._state.enforced = True

        self._clear_bossbar()
        self._announce("Goodnight. The server is closing.")
        self._run("save-all")

        if self.config.action == ACTION_KICK:
            self._run("kick @a The server is closed until morning. Goodnight!")
        elif self.config.action == ACTION_STOP:
            if self.stopper is not None:
                try:
                    self.stopper()
                except Exception as exc:  # noqa: BLE001 - report and carry on
                    self._log_error(f"Bedtime could not stop the server: {exc}")
            else:
                self._run("stop")

    def on_player_join(self, event, now: Optional[datetime] = None) -> None:
        """Turn players away while the window is closed.

        Subscribed to the event bus. Stopping the server is not enough by
        itself: a restart policy or an update timer can bring it back, and then
        the evening is open again. This is what actually holds the line.

        The kick is queued rather than sent here. Event bus handlers run on the
        thread that follows the server log, and sending a command makes a
        network call that can block for as long as its timeouts allow. The
        bedtime thread picks it up, normally within a few milliseconds.
        """
        if getattr(event, "type", None) != "join" or not event.player:
            return

        now = now or datetime.now()
        if not self.is_closed(now):
            return

        opens = self.wake_after(self._night_of(now)).strftime("%H:%M")
        self._actions.put(f"kick {event.player} The server is closed until {opens}. Goodnight!")

    def pending_actions(self) -> int:
        """How many queued commands are waiting. Used by tests."""
        return self._actions.qsize()

    def run_pending(self, limit: int = 100) -> int:
        """Send queued commands now. Returns how many were sent.

        The loop calls this; tests call it directly instead of starting a thread.
        """
        sent = 0
        while sent < limit:
            try:
                command = self._actions.get_nowait()
            except queue.Empty:
                break
            if command is None:
                break
            self._run(command)
            sent += 1
        return sent

    def _announce(self, message: str) -> None:
        self._run(f'tellraw @a {{"text":"{message}","color":"aqua"}}')

    def _title(self, message: str) -> None:
        self._run(f'title @a title {{"text":"{message}","color":"gold"}}')

    # Background thread

    def start(self) -> None:
        """Begin ticking on a background thread."""
        with self._lock:
            if self._thread is not None:
                return
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._loop, daemon=True, name="bedtime")
            self._thread.start()

    def stop(self, timeout: float = 5.0) -> None:
        """Stop ticking."""
        with self._lock:
            thread, self._thread = self._thread, None
        if thread is None:
            return
        self._stop_event.set()
        # Wake the loop immediately rather than waiting out its timeout.
        self._actions.put(None)
        thread.join(timeout)

    def _loop(self) -> None:
        """Tick on a schedule, but act on queued commands straight away."""
        next_tick = time_module.monotonic()

        while not self._stop_event.is_set():
            timeout = max(0.05, next_tick - time_module.monotonic())
            try:
                command = self._actions.get(timeout=timeout)
            except queue.Empty:
                command = None

            if command is not None:
                self._run(command)

            if time_module.monotonic() >= next_tick:
                try:
                    self.tick()
                except Exception as exc:  # noqa: BLE001 - must outlive a bad tick
                    self._log_error(f"Bedtime tick failed: {exc}")
                next_tick = time_module.monotonic() + TICK_SECONDS


_bedtime: Optional[Bedtime] = None
_bedtime_lock = threading.Lock()


def get_bedtime(
    runner: Optional[Callable[[str], None]] = None,
    stopper: Optional[Callable[[], None]] = None,
) -> Bedtime:
    """Return the shared Bedtime, built from config on first use."""
    global _bedtime
    with _bedtime_lock:
        if _bedtime is None:
            _bedtime = Bedtime(config=load_bedtime_config(), runner=runner, stopper=stopper)
        else:
            if runner is not None and _bedtime.runner is None:
                _bedtime.runner = runner
            if stopper is not None and _bedtime.stopper is None:
                _bedtime.stopper = stopper
        return _bedtime


def reset_bedtime() -> None:
    """Drop the shared instance. Used by tests."""
    global _bedtime
    with _bedtime_lock:
        if _bedtime is not None:
            _bedtime.stop()
        _bedtime = None
