#!/usr/bin/env python3
"""Player statistics, read from the files the game itself writes.

Minecraft keeps authoritative per-player counters in
``<world>/stats/<uuid>.json`` and completed advancements in
``<world>/advancements/<uuid>.json``. They cover every statistic the game
tracks: blocks mined by type, distance travelled, damage taken, time played,
every death.

This replaces ``scripts/player-stats-tracker.sh``, which scraped the server log
with three regular expressions and *added* what it found to the previous
totals, so the numbers climbed on every run whether or not anything had
happened, and a restart replayed the whole file. Reading the game's own counters
is idempotent by construction: there is nothing to accumulate, because the
number in the file is the answer.

Names come from ``usercache.json``, which the server maintains alongside the
world.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

PROJECT_ROOT = Path(__file__).parent.parent

# Ticks per second, and therefore what the play-time counters are measured in.
TICKS_PER_SECOND = 20

# Vanilla stores stats under these top-level keys. "custom" holds the scalar
# counters; the rest are maps of item or entity id to a count.
CUSTOM = "minecraft:custom"
MINED = "minecraft:mined"
CRAFTED = "minecraft:crafted"
USED = "minecraft:used"
KILLED = "minecraft:killed"
KILLED_BY = "minecraft:killed_by"

# Play time was renamed in 1.17. Both are in ticks, despite the older name.
PLAY_TIME_KEYS = ("minecraft:play_time", "minecraft:play_one_minute")


def _server_properties_path() -> Optional[Path]:
    """server.properties as the running server sees it.

    docker-compose mounts ./data as the server directory, so that copy is the
    live one; a copy at the project root is a leftover and only used as a
    fallback.
    """
    for candidate in (PROJECT_ROOT / "data" / "server.properties", PROJECT_ROOT / "server.properties"):
        if candidate.exists():
            return candidate
    return None


def world_name() -> str:
    """The active world, from level-name in server.properties."""
    path = _server_properties_path()
    if path is None:
        return "world"
    try:
        for line in path.read_text().splitlines():
            if line.startswith("level-name="):
                name = line.split("=", 1)[1].strip()
                if name:
                    return name
    except OSError:
        # Unreadable server.properties: fall through to the default below
        # rather than failing. A missing world name is not worth a 500, and
        # "world" is what the server itself defaults to.
        pass
    return "world"


def world_dir() -> Path:
    """Where the world's data lives.

    ``MC_WORLD_DIR`` overrides it outright, for a server whose files are not
    under ``data/`` — the same escape hatch MC_EVENTS_DIR provides.
    """
    configured = os.environ.get("MC_WORLD_DIR", "").strip()
    if configured:
        return Path(configured).expanduser()
    return PROJECT_ROOT / "data" / world_name()


def _load_json(path: Path) -> Optional[dict]:
    """Read a JSON file, treating anything unreadable as absent.

    The server writes these files while running, so a read can land mid-write.
    A missing statistic is better than a 500.
    """
    try:
        with open(path, "r") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def load_usercache() -> Dict[str, str]:
    """Map player UUID to name, from the server's usercache.json."""
    for candidate in (world_dir().parent / "usercache.json", PROJECT_ROOT / "data" / "usercache.json"):
        if not candidate.exists():
            continue
        try:
            with open(candidate, "r") as handle:
                entries = json.load(handle)
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(entries, list):
            return {
                entry["uuid"]: entry["name"]
                for entry in entries
                if isinstance(entry, dict) and "uuid" in entry and "name" in entry
            }
    return {}


@dataclass
class PlayerStats:
    """One player's counters, derived from the game's own files."""

    uuid: str
    name: str
    play_time_minutes: int = 0
    deaths: int = 0
    mob_kills: int = 0
    player_kills: int = 0
    blocks_mined: int = 0
    items_crafted: int = 0
    damage_taken: int = 0
    damage_dealt: int = 0
    jumps: int = 0
    distance_walked_m: int = 0
    advancements: int = 0
    # The complete stats block, for anything the summary above does not name.
    raw: Dict[str, Any] = field(default_factory=dict)

    def as_dict(self, include_raw: bool = False) -> Dict[str, Any]:
        data = {
            "uuid": self.uuid,
            "name": self.name,
            "play_time_minutes": self.play_time_minutes,
            "deaths": self.deaths,
            "mob_kills": self.mob_kills,
            "player_kills": self.player_kills,
            "blocks_mined": self.blocks_mined,
            "items_crafted": self.items_crafted,
            "damage_taken": self.damage_taken,
            "damage_dealt": self.damage_dealt,
            "jumps": self.jumps,
            "distance_walked_m": self.distance_walked_m,
            "advancements": self.advancements,
        }
        if include_raw:
            data["raw"] = self.raw
        return data


def _custom(stats: dict, key: str, default: int = 0) -> int:
    value = stats.get(CUSTOM, {}).get(key, default)
    return value if isinstance(value, int) else default


def _sum_section(stats: dict, section: str) -> int:
    values = stats.get(section, {})
    if not isinstance(values, dict):
        return 0
    return sum(v for v in values.values() if isinstance(v, int))


def _play_time_ticks(stats: dict) -> int:
    for key in PLAY_TIME_KEYS:
        ticks = _custom(stats, key, 0)
        if ticks:
            return ticks
    return 0


def _count_advancements(uuid: str) -> int:
    """How many advancements the player has completed."""
    data = _load_json(world_dir() / "advancements" / f"{uuid}.json")
    if not data:
        return 0
    done = 0
    for key, value in data.items():
        # DataVersion sits alongside the advancements as a bare int.
        if not isinstance(value, dict):
            continue
        # Recipe advancements are how recipes unlock; they are not achievements
        # and counting them makes the number meaningless.
        if key.startswith("minecraft:recipes/"):
            continue
        if value.get("done") is True:
            done += 1
    return done


def read_player(uuid: str, names: Optional[Dict[str, str]] = None) -> Optional[PlayerStats]:
    """Build one player's statistics, or None if the game has no file for them."""
    data = _load_json(world_dir() / "stats" / f"{uuid}.json")
    if data is None:
        return None

    stats = data.get("stats", {})
    if not isinstance(stats, dict):
        stats = {}

    names = names if names is not None else load_usercache()

    return PlayerStats(
        uuid=uuid,
        name=names.get(uuid, uuid),
        # Ticks to whole minutes. Rounding down matches how a player would
        # describe their own play time.
        play_time_minutes=_play_time_ticks(stats) // (TICKS_PER_SECOND * 60),
        deaths=_custom(stats, "minecraft:deaths"),
        mob_kills=_custom(stats, "minecraft:mob_kills"),
        player_kills=_custom(stats, "minecraft:player_kills"),
        blocks_mined=_sum_section(stats, MINED),
        items_crafted=_sum_section(stats, CRAFTED),
        # The damage counters are in tenths of a heart.
        damage_taken=_custom(stats, "minecraft:damage_taken") // 10,
        damage_dealt=_custom(stats, "minecraft:damage_dealt") // 10,
        jumps=_custom(stats, "minecraft:jump"),
        # Distances are in centimetres.
        distance_walked_m=_custom(stats, "minecraft:walk_one_cm") // 100,
        advancements=_count_advancements(uuid),
        raw=stats,
    )


def _stat_files() -> Iterator[Path]:
    stats_dir = world_dir() / "stats"
    if not stats_dir.is_dir():
        return iter(())
    return stats_dir.glob("*.json")


def read_all() -> List[PlayerStats]:
    """Every player the world has a statistics file for."""
    names = load_usercache()
    players = []
    for path in _stat_files():
        player = read_player(path.stem, names)
        if player is not None:
            players.append(player)
    players.sort(key=lambda p: p.name.lower())
    return players


def find_by_name(name: str) -> Optional[PlayerStats]:
    """Look a player up by name, as the API's callers do."""
    names = load_usercache()
    wanted = name.lower()
    for uuid, cached in names.items():
        if cached.lower() == wanted:
            return read_player(uuid, names)

    # Not in the usercache: fall back to scanning, so a player whose cache
    # entry has expired is still reachable.
    for player in read_all():
        if player.name.lower() == wanted:
            return player
    return None


# The metrics a leaderboard can be built on, and what they mean. The keys are
# the fields of PlayerStats, so a caller can discover them from one place.
LEADERBOARD_METRICS = {
    "play_time_minutes": "Minutes played",
    "deaths": "Deaths",
    "mob_kills": "Mobs killed",
    "player_kills": "Players killed",
    "blocks_mined": "Blocks mined",
    "items_crafted": "Items crafted",
    "damage_taken": "Damage taken, in hearts",
    "damage_dealt": "Damage dealt, in hearts",
    "jumps": "Jumps",
    "distance_walked_m": "Distance walked, in metres",
    "advancements": "Advancements completed",
}

# The old log-scraping tracker invented its own names. Map them onto the real
# counters so an existing caller keeps working instead of silently getting a
# zeroed leaderboard.
METRIC_ALIASES = {
    "login_count": "play_time_minutes",
    "logout_count": "play_time_minutes",
    "blocks_broken": "blocks_mined",
    "play_time": "play_time_minutes",
}


def resolve_metric(metric: str) -> Optional[str]:
    """Normalise a requested metric, or None if there is no such counter."""
    metric = (metric or "").strip()
    metric = METRIC_ALIASES.get(metric, metric)
    return metric if metric in LEADERBOARD_METRICS else None


def leaderboard(metric: str, limit: int = 10) -> Dict[str, Any]:
    """Rank players by one counter, highest first."""
    resolved = resolve_metric(metric)
    if resolved is None:
        raise ValueError(f"Unknown metric '{metric}'. Valid: {', '.join(sorted(LEADERBOARD_METRICS))}")

    players = read_all()
    players.sort(key=lambda p: getattr(p, resolved), reverse=True)
    top = players[: max(0, limit)]

    return {
        "metric": resolved,
        "description": LEADERBOARD_METRICS[resolved],
        "leaderboard": [
            {"name": p.name, "uuid": p.uuid, "value": getattr(p, resolved)} for p in top
        ],
    }
