#!/usr/bin/env python3
"""The Pet Cemetery: gentle obituaries and gravestones for named pets.

Subscribes to pet-death events from :mod:`api.events`, writes a gentle
epitaph (reusing :mod:`api.epitaphs`'s cause classification, but its own
templates -- a tamed wolf's death shouldn't read like the Hall of Deaths'
Victorian-newspaper joke), keeps a record, and places a small gravestone
sign in the cemetery over RCON.

Deliberately not part of ``api.hall_of_deaths``: pets aren't players, the
tone is different by design (docs/ROADMAP.md: "announce it gently rather
than with the comedy tone the player obituaries use"), and the vanilla log
line that reports a pet's death names no owner at all, so this doesn't try
to attribute a death to a person -- there is nothing in the event to
attribute it with. Mirrors ``hall_of_deaths.py``'s shape (the same
handler/worker/record/JSONL pattern), not its class.
"""

from __future__ import annotations

import hashlib
import json
import queue
import threading
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Optional

from api.epitaphs import classify_cause, extract_culprit

PROJECT_ROOT = Path(__file__).parent.parent
PET_CEMETERY_DIR = PROJECT_ROOT / "data" / "pet_cemetery"

DEFAULT_RETENTION_DAYS = 365

# Where the cemetery is in the world, and how plots are laid out. Coordinates
# are a placeholder -- same pattern as the family datapack's Neighbors
# advancement -- edit once to a real spot near the house. Read fresh on every
# gravestone placement rather than baked into a datapack, so no /reload is
# needed after changing it.
CEMETERY_ORIGIN = (100, 64, 200)
CEMETERY_PLOT_SPACING = 2
CEMETERY_ROW_LENGTH = 10

# Best-effort mapping from the Java entity class name Minecraft's own log
# line names (e.g. "EntityWolf") to a friendly species word. Verified only
# against one real example (EntityBlaze, from a captured server log); the
# rest follow the same "Entity" + capitalized-name pattern by inference.
# Getting one wrong just means "pet" instead of "dog" on a gravestone, not a
# broken feature, so this stays a best-effort table rather than something
# worth more research to nail down exactly.
FRIENDLY_SPECIES = {
    "EntityWolf": "dog",
    "EntityCat": "cat",
    "EntityOcelot": "cat",
    "EntityParrot": "parrot",
    "EntityHorse": "horse",
    "EntityDonkey": "donkey",
    "EntityMule": "mule",
    "EntityLlama": "llama",
    "EntityTraderLlama": "llama",
    "EntityCamel": "camel",
}

# Gentle epitaphs, keyed by the same cause categories api.epitaphs.classify_cause
# already produces. Deliberately not the Hall of Deaths' comedic templates --
# this reuses only the cause-classification utility, not the tone. Covers the
# categories a pet is actually likely to die from; anything else falls back
# to "unknown", which is written to read fine for a cause we don't have a
# specific line for rather than sounding like a missing case.
GENTLE_EPITAPHS: dict[str, tuple[str, ...]] = {
    "combat": (
        "{name} looked after this family for as long as they could.",
        "{name} did not come home tonight. They are missed already.",
        "{name} is remembered for the good years, not the last moment.",
    ),
    "explosion": (
        "{name} was caught in something no one could have stopped in time.",
        "{name} is gone, suddenly and without warning.",
    ),
    "fall": (
        "{name} loved to explore. That love took them somewhere they could not come back from.",
        "{name} is remembered for their curiosity.",
    ),
    "drowning": (
        "{name} is at rest now, somewhere calmer than water.",
        "{name} will be missed on quiet walks.",
    ),
    "fire": (
        "{name} is remembered warmly.",
        "{name}'s spark is missed.",
    ),
    "lava": (
        "{name} wandered somewhere too dangerous to follow.",
        "{name} is remembered fondly.",
    ),
    "lightning": (
        "{name} was taken suddenly, in a moment no one could have prevented.",
        "{name} is missed under calmer skies.",
    ),
    "void": (
        "{name} is gone somewhere none of us can follow.",
        "{name} will be remembered, wherever they've gone.",
    ),
    "starvation": (
        "{name} is at peace now.",
        "{name} will be missed at mealtimes.",
    ),
    "freezing": (
        "{name} is remembered for the warmth they brought, not the cold.",
        "{name} is at rest now.",
    ),
    "unknown": (
        "{name} is missed.",
        "{name} will be remembered fondly.",
        "Here rests {name}, a good companion.",
    ),
}


@dataclass(frozen=True)
class PetDeath:
    """The facts of one pet's death, as the epitaph writer needs them."""

    entity_type: str
    name: str
    cause: str
    timestamp: str = ""

    @property
    def category(self) -> str:
        return classify_cause(self.cause)

    @property
    def culprit(self) -> Optional[str]:
        return extract_culprit(self.cause)

    @property
    def species(self) -> str:
        return FRIENDLY_SPECIES.get(self.entity_type, "pet")


def write_gentle_epitaph(death: PetDeath) -> str:
    """Write a gentle, non-comedic epitaph for a pet's death."""
    options = GENTLE_EPITAPHS.get(death.category, GENTLE_EPITAPHS["unknown"])
    # Same stable-choice-by-hash technique as api.epitaphs, minus the extra
    # per-death randomness seed: pets don't die often enough on a family
    # server for two identical-looking epitaphs in a row to be a real
    # concern the way it is for player deaths.
    digest = hashlib.sha256(f"{death.name}|{death.cause}".encode("utf-8")).digest()
    template = options[int.from_bytes(digest[:4], "big") % len(options)]
    return template.format(name=death.name)


@dataclass(frozen=True)
class PetDeathRecord:
    """One pet's death, with the epitaph and gravestone plot assigned to it."""

    name: str
    species: str
    cause: str
    category: str
    epitaph: str
    timestamp: str
    plot: int
    culprit: Optional[str] = None
    gravestone_placed: bool = False

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), separators=(",", ":"))


def plot_position(plot: int) -> tuple[int, int, int]:
    """Where the Nth gravestone goes, laid out in rows from the cemetery origin."""
    ox, oy, oz = CEMETERY_ORIGIN
    row, col = divmod(plot, CEMETERY_ROW_LENGTH)
    return (ox + col * CEMETERY_PLOT_SPACING, oy, oz + row * CEMETERY_PLOT_SPACING)


def build_gravestone_commands(record: PetDeathRecord) -> list[str]:
    """RCON commands that place one gravestone sign for a recorded death."""
    x, y, z = plot_position(record.plot)
    date = record.timestamp[:10] if record.timestamp else ""
    lines = [
        f"{record.name}",
        f"the {record.species}" if record.species != "pet" else "a pet",
        date,
        record.epitaph[:32],
    ]
    commands = [f"setblock {x} {y} {z} minecraft:oak_sign"]
    for index, text in enumerate(lines):
        escaped = text.replace("\\", "\\\\").replace('"', '\\"')
        commands.append(f'data modify block {x} {y} {z} front_text.messages[{index}] set value "{escaped}"')
    return commands


class PetCemetery:
    """Records pet deaths, writes gentle epitaphs and places gravestones."""

    def __init__(
        self,
        cemetery_dir: Optional[Path] = None,
        runner: Optional[Callable[[str], None]] = None,
        retention_days: int = DEFAULT_RETENTION_DAYS,
    ) -> None:
        self.cemetery_dir = cemetery_dir if cemetery_dir is not None else PET_CEMETERY_DIR
        self.runner = runner
        self.retention_days = retention_days

        self._lock = threading.Lock()
        self._error_logger: Optional[Callable[[str], None]] = None
        self._last_pruned_date: Optional[str] = None
        self._next_plot: Optional[int] = None

        self._queue: Optional[queue.Queue] = None
        self._worker: Optional[threading.Thread] = None
        self._pending = 0
        self._pending_cv = threading.Condition()

    def set_error_logger(self, logger: Callable[[str], None]) -> None:
        self._error_logger = logger

    def _log_error(self, message: str) -> None:
        if self._error_logger is not None:
            try:
                self._error_logger(message)
            except Exception:  # noqa: BLE001 - reporting a failure must not fail
                pass

    def handle_event(self, event) -> Optional[PetDeathRecord]:
        """Event bus handler. Ignores everything that is not a pet death."""
        if getattr(event, "type", None) != "pet_death":
            return None

        death = PetDeath(
            entity_type=event.data.get("entity_type", ""),
            name=event.data.get("name", ""),
            cause=event.data.get("cause", ""),
            timestamp=event.timestamp,
        )
        if not death.name:
            return None

        if self._queue is not None:
            with self._pending_cv:
                self._pending += 1
            self._queue.put(death)
            return None

        return self.record(death)

    def record(self, death: PetDeath) -> PetDeathRecord:
        """Assign a plot, write the epitaph, place the gravestone, then store it."""
        epitaph = write_gentle_epitaph(death)
        plot = self._claim_next_plot()

        record = PetDeathRecord(
            name=death.name,
            species=death.species,
            cause=death.cause,
            category=death.category,
            epitaph=epitaph,
            timestamp=death.timestamp or datetime.now(timezone.utc).isoformat(),
            plot=plot,
            culprit=death.culprit,
            gravestone_placed=False,
        )

        placed = False
        if self.runner is not None:
            try:
                for command in build_gravestone_commands(record):
                    self.runner(command)
                placed = True
            except Exception as exc:  # noqa: BLE001 - the game may be down
                self._log_error(f"Could not place a gravestone for {death.name}: {exc}")

        if placed:
            record = PetDeathRecord(**{**record.to_dict(), "gravestone_placed": True})

        self._append(record)
        return record

    def start_worker(self) -> None:
        """Handle pet deaths on a background thread instead of inline.

        Same reasoning as HallOfDeaths.start_worker(): placing a gravestone
        is a handful of RCON round trips, and event bus handlers run on the
        log follower thread.
        """
        with self._lock:
            if self._worker is not None:
                return
            self._queue = queue.Queue()
            self._worker = threading.Thread(target=self._work, daemon=True, name="pet-cemetery")
            self._worker.start()

    def stop_worker(self, timeout: float = 5.0) -> None:
        with self._lock:
            worker, self._worker = self._worker, None
            work_queue, self._queue = self._queue, None

        if worker is None or work_queue is None:
            return

        work_queue.put(None)
        worker.join(timeout)

    def drain(self, timeout: float = 5.0) -> bool:
        """Block until queued pet deaths have been processed. Used by tests."""
        with self._pending_cv:
            return self._pending_cv.wait_for(lambda: self._pending == 0, timeout=timeout)

    def _work(self) -> None:
        while True:
            death = self._queue.get() if self._queue is not None else None
            if death is None:
                return
            try:
                self.record(death)
            except Exception as exc:  # noqa: BLE001 - one bad death must not end the worker
                self._log_error(f"Could not process a pet death: {exc}")
            finally:
                with self._pending_cv:
                    self._pending -= 1
                    self._pending_cv.notify_all()

    def _claim_next_plot(self) -> int:
        """Return the next free plot index, persisted across restarts.

        A plain incrementing counter in a state file, not a live scoreboard
        round trip -- this module already owns the bookkeeping, the same way
        scripts/command-scheduler.py owns its own schedule file rather than
        asking the game for it.
        """
        with self._lock:
            if self._next_plot is None:
                self._next_plot = self._read_next_plot()
            plot = self._next_plot
            self._next_plot += 1
            self._write_next_plot(self._next_plot)
            return plot

    def _state_file(self) -> Path:
        return self.cemetery_dir / "state.json"

    def _read_next_plot(self) -> int:
        path = self._state_file()
        if not path.exists():
            return 0
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return int(data.get("next_plot", 0))
        except (OSError, ValueError):
            return 0

    def _write_next_plot(self, next_plot: int) -> None:
        path = self._state_file()
        try:
            self.cemetery_dir.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps({"next_plot": next_plot}), encoding="utf-8")
        except OSError as exc:
            self._log_error(f"Could not persist the next cemetery plot: {exc}")

    def _append(self, record: PetDeathRecord) -> None:
        day = record.timestamp[:10] or datetime.now(timezone.utc).strftime("%Y-%m-%d")
        try:
            with self._lock:
                self.cemetery_dir.mkdir(parents=True, exist_ok=True)
                with open(self.cemetery_dir / f"{day}.jsonl", "a", encoding="utf-8") as handle:
                    handle.write(record.to_json() + "\n")
        except OSError as exc:
            self._log_error(f"Could not record a pet death: {exc}")
            return

        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if self._last_pruned_date != today:
            self._last_pruned_date = today
            self.prune()

    def _iter_records(self):
        if not self.cemetery_dir.exists():
            return
        for path in sorted(self.cemetery_dir.glob("*.jsonl"), reverse=True):
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
                    continue

    def read(self, limit: int = 50) -> list[dict]:
        """Return recent pet death records, newest first."""
        collected: list[dict] = []
        for record in self._iter_records():
            collected.append(record)
            if len(collected) >= limit:
                break
        return collected

    def prune(self) -> int:
        """Delete daily files past the retention window."""
        if self.retention_days <= 0 or not self.cemetery_dir.exists():
            return 0

        cutoff = (datetime.now(timezone.utc) - timedelta(days=self.retention_days)).date()
        removed = 0
        for path in self.cemetery_dir.glob("*.jsonl"):
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


_cemetery: Optional[PetCemetery] = None
_cemetery_lock = threading.Lock()


def get_cemetery(runner: Optional[Callable[[str], None]] = None) -> PetCemetery:
    """Return the shared Pet Cemetery, built on first use."""
    global _cemetery
    with _cemetery_lock:
        if _cemetery is None:
            _cemetery = PetCemetery(runner=runner)
        elif runner is not None and _cemetery.runner is None:
            _cemetery.runner = runner
        return _cemetery


def reset_cemetery() -> None:
    """Drop the shared instance. Used by tests."""
    global _cemetery
    with _cemetery_lock:
        if _cemetery is not None:
            _cemetery.stop_worker()
        _cemetery = None
