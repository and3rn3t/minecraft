#!/usr/bin/env python3
"""The Hall of Deaths: epitaphs for every death, in game and on the dashboard.

Subscribes to death events from :mod:`api.events`, has :mod:`api.epitaphs` write
an obituary, announces it to everyone online over RCON, and keeps the record so
the dashboard can show a hall of fame and a leaderboard.

This is the first feature built on the event bus, and it is deliberately a
complete vertical slice: an event arrives, something happens in the game, and a
record survives for later. Anything else that wants to react to play follows the
same shape.
"""

from __future__ import annotations

import json
import threading
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Optional

from api.epitaphs import Death, EpitaphWriter, write_epitaph

PROJECT_ROOT = Path(__file__).parent.parent
DEATHS_DIR = PROJECT_ROOT / "data" / "deaths"
DEATHS_CONFIG_FILE = PROJECT_ROOT / "config" / "deaths.conf"

DEFAULT_RETENTION_DAYS = 365
# Minecraft truncates long RCON commands, and an epitaph is a single line
# anyway. The margin leaves room for the tellraw wrapper and JSON escaping.
MAX_ANNOUNCEMENT_LENGTH = 220

DEFAULT_ANNOUNCE = True
DEFAULT_COLOR = "gray"


@dataclass(frozen=True)
class DeathRecord:
    """One death, with the epitaph that was written for it."""

    player: str
    cause: str
    category: str
    epitaph: str
    timestamp: str
    culprit: Optional[str] = None
    message: str = ""
    announced: bool = False

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), separators=(",", ":"))


def load_deaths_config(config_file: Optional[Path] = None) -> dict:
    """Read ``config/deaths.conf``, falling back to defaults.

    Shell-style ``KEY=value`` assignments, matching every other config file in
    the project. See ``config/deaths.conf.example``.
    """
    path = config_file if config_file is not None else DEATHS_CONFIG_FILE
    settings = {
        "announce": DEFAULT_ANNOUNCE,
        "color": DEFAULT_COLOR,
        "retention_days": DEFAULT_RETENTION_DAYS,
    }

    if not path.exists():
        return settings

    try:
        content = path.read_text(encoding="utf-8")
    except OSError:
        return settings

    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("\"'")

        if key == "ANNOUNCE_IN_GAME":
            settings["announce"] = value.lower() in ("1", "true", "yes", "on")
        elif key == "ANNOUNCE_COLOR" and value:
            settings["color"] = value
        elif key == "RETENTION_DAYS":
            try:
                settings["retention_days"] = int(value)
            except ValueError:
                # A typo in the config should not stop the server from starting.
                # The default retention stays in place and the Hall still works.
                pass

    return settings


def build_tellraw(epitaph: str, color: str = DEFAULT_COLOR) -> str:
    """Build the ``tellraw`` that shows an epitaph to everyone online.

    The text is JSON-encoded rather than interpolated, so an epitaph containing
    a quote or a backslash cannot break the command or inject extra components.
    """
    text = epitaph
    if len(text) > MAX_ANNOUNCEMENT_LENGTH:
        text = text[: MAX_ANNOUNCEMENT_LENGTH - 1].rstrip() + "…"

    component = json.dumps({"text": text, "color": color, "italic": True}, ensure_ascii=False)
    return f"tellraw @a {component}"


class HallOfDeaths:
    """Records deaths, writes their epitaphs and announces them in game."""

    def __init__(
        self,
        deaths_dir: Optional[Path] = None,
        writer: Optional[EpitaphWriter] = None,
        announcer: Optional[Callable[[str], None]] = None,
        announce: bool = DEFAULT_ANNOUNCE,
        color: str = DEFAULT_COLOR,
        retention_days: int = DEFAULT_RETENTION_DAYS,
    ) -> None:
        self.deaths_dir = deaths_dir if deaths_dir is not None else DEATHS_DIR
        self.writer = writer
        self.announcer = announcer
        self.announce = announce
        self.color = color
        self.retention_days = retention_days

        self._lock = threading.Lock()
        self._error_logger: Optional[Callable[[str], None]] = None
        self._last_pruned_date: Optional[str] = None

    def set_error_logger(self, logger: Callable[[str], None]) -> None:
        self._error_logger = logger

    def _log_error(self, message: str) -> None:
        if self._error_logger is not None:
            try:
                self._error_logger(message)
            except Exception:  # noqa: BLE001 - reporting a failure must not fail
                # The logger is supplied by the caller and may be closed or
                # broken. Losing the report is preferable to raising on the
                # thread that feeds the event bus.
                pass

    def handle_event(self, event) -> Optional[DeathRecord]:
        """Event bus handler. Ignores everything that is not a death."""
        if getattr(event, "type", None) != "death":
            return None
        if not event.player:
            return None

        death = Death(
            player=event.player,
            cause=event.data.get("cause", ""),
            message=event.data.get("message", ""),
            timestamp=event.timestamp,
        )
        return self.record(death)

    def record(self, death: Death) -> DeathRecord:
        """Write the epitaph, persist the record, then announce it.

        Persisting comes first on purpose. Announcing needs the game server to
        be reachable, and a death is worth keeping even when the announcement
        cannot be delivered.
        """
        epitaph = write_epitaph(death, self.writer)
        record = DeathRecord(
            player=death.player,
            cause=death.cause,
            category=death.category,
            epitaph=epitaph,
            timestamp=death.timestamp or datetime.now(timezone.utc).isoformat(),
            culprit=death.culprit,
            message=death.message,
            announced=False,
        )

        self._append(record)

        if self.announce and self.announcer is not None:
            try:
                self.announcer(build_tellraw(epitaph, self.color))
                record = DeathRecord(**{**record.to_dict(), "announced": True})
            except Exception as exc:  # noqa: BLE001 - the game may be down
                self._log_error(f"Could not announce a death in game: {exc}")

        return record

    def _append(self, record: DeathRecord) -> None:
        """Append one record to today's file.

        Deaths are rare enough that they are written immediately rather than
        batched like log events. Losing a funny epitaph to a crash would be a
        worse trade than the handful of extra writes.
        """
        day = record.timestamp[:10] or datetime.now(timezone.utc).strftime("%Y-%m-%d")
        try:
            with self._lock:
                self.deaths_dir.mkdir(parents=True, exist_ok=True)
                with open(self.deaths_dir / f"{day}.jsonl", "a", encoding="utf-8") as handle:
                    handle.write(record.to_json() + "\n")
        except OSError as exc:
            self._log_error(f"Could not record a death: {exc}")
            return

        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if self._last_pruned_date != today:
            self._last_pruned_date = today
            self.prune()

    def _iter_records(self):
        """Yield every stored record, newest file first, newest line first."""
        if not self.deaths_dir.exists():
            return
        for path in sorted(self.deaths_dir.glob("*.jsonl"), reverse=True):
            try:
                lines = path.read_text(encoding="utf-8").splitlines()
            except OSError:
                continue
            for line in reversed(lines):
                line = line.strip()
                if not line:
                    continue
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    # A torn final line from an interrupted write.
                    continue

    def read(self, limit: int = 50, player: Optional[str] = None, category: Optional[str] = None) -> list[dict]:
        """Return recent death records, newest first."""
        collected: list[dict] = []
        for record in self._iter_records():
            if player and record.get("player") != player:
                continue
            if category and record.get("category") != category:
                continue
            collected.append(record)
            if len(collected) >= limit:
                break
        return collected

    def leaderboard(self, limit: int = 10) -> list[dict]:
        """Per-player death totals, most deaths first.

        Each entry carries the player's most frequent way of dying and their
        most recent epitaph, which is the part anybody actually reads.

        ``favourite_cause_count`` is included because a "favourite" is only
        meaningful once it has happened more than once. Four deaths in four
        different ways have no mode, and a caller that says "mostly drowning"
        on the strength of a single drowning is telling a small lie. Callers
        should check the count before using the word.
        """
        totals: dict[str, dict] = {}

        for record in self._iter_records():
            player = record.get("player")
            if not player:
                continue

            category = record.get("category", "unknown")
            entry = totals.get(player)
            if entry is None:
                # Records arrive newest first, so the first one seen for a
                # player is their most recent.
                entry = {
                    "player": player,
                    "deaths": 0,
                    "categories": {},
                    "last_epitaph": record.get("epitaph", ""),
                    "last_death": record.get("timestamp", ""),
                    "last_category": category,
                }
                totals[player] = entry

            entry["deaths"] += 1
            entry["categories"][category] = entry["categories"].get(category, 0) + 1

        ranked = []
        for entry in totals.values():
            categories = entry.pop("categories")
            if categories:
                # Sort by count, then by name, so a tie always resolves the
                # same way rather than following dict insertion order.
                favourite, count = sorted(categories.items(), key=lambda item: (-item[1], item[0]))[0]
            else:
                favourite, count = "unknown", 0

            entry["favourite_cause"] = favourite
            entry["favourite_cause_count"] = count
            entry["causes"] = categories
            ranked.append(entry)

        ranked.sort(key=lambda item: (-item["deaths"], item["player"]))
        return ranked[:limit]

    def stats(self) -> dict:
        """Totals across everyone, for the summary tiles."""
        records = list(self._iter_records())
        categories: dict[str, int] = {}
        for record in records:
            category = record.get("category", "unknown")
            categories[category] = categories.get(category, 0) + 1

        return {
            "total_deaths": len(records),
            "players": len({r.get("player") for r in records if r.get("player")}),
            "categories": categories,
            "most_common_cause": max(categories, key=categories.get) if categories else None,
        }

    def prune(self) -> int:
        """Delete daily files past the retention window."""
        if self.retention_days <= 0 or not self.deaths_dir.exists():
            return 0

        cutoff = (datetime.now(timezone.utc) - timedelta(days=self.retention_days)).date()
        removed = 0
        for path in self.deaths_dir.glob("*.jsonl"):
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


_hall: Optional[HallOfDeaths] = None
_hall_lock = threading.Lock()


def get_hall(announcer: Optional[Callable[[str], None]] = None) -> HallOfDeaths:
    """Return the shared Hall of Deaths, built from config on first use."""
    global _hall
    with _hall_lock:
        if _hall is None:
            settings = load_deaths_config()
            _hall = HallOfDeaths(
                announcer=announcer,
                announce=settings["announce"],
                color=settings["color"],
                retention_days=settings["retention_days"],
            )
        elif announcer is not None and _hall.announcer is None:
            _hall.announcer = announcer
        return _hall


def reset_hall() -> None:
    """Drop the shared instance. Used by tests."""
    global _hall
    with _hall_lock:
        _hall = None
