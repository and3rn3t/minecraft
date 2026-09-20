#!/usr/bin/env python3
"""Tests for player statistics read from the game's own files.

The tracker these replaced scraped the server log and added what it found to
the previous totals, so the same unchanged log reported 1, then 2, then 3. The
property that matters here is that reading is idempotent, and the first test
says so.
"""

import json
import sys
from pathlib import Path as PathLib

import pytest

PROJECT_ROOT = PathLib(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import api.player_stats as player_stats  # noqa: E402
import api.server as api_module  # noqa: E402

JONAH = "11111111-1111-1111-1111-111111111111"
SILAS = "22222222-2222-2222-2222-222222222222"
GHOST = "33333333-3333-3333-3333-333333333333"


@pytest.fixture
def world(tmp_path, monkeypatch):
    """A world directory shaped like the one the server writes."""
    world_dir = tmp_path / "world"
    (world_dir / "stats").mkdir(parents=True)
    (world_dir / "advancements").mkdir(parents=True)

    (world_dir / "stats" / f"{JONAH}.json").write_text(
        json.dumps(
            {
                "stats": {
                    "minecraft:custom": {
                        "minecraft:play_time": 1_440_000,  # ticks -> 1200 minutes
                        "minecraft:deaths": 7,
                        "minecraft:mob_kills": 120,
                        "minecraft:jump": 4200,
                        "minecraft:walk_one_cm": 1_234_500,  # cm -> 12345 m
                        "minecraft:damage_taken": 3_400,  # tenths of a heart -> 340
                        "minecraft:damage_dealt": 9_900,
                    },
                    "minecraft:mined": {"minecraft:stone": 5000, "minecraft:dirt": 1200},
                    "minecraft:crafted": {"minecraft:torch": 64},
                },
                "DataVersion": 3700,
            }
        )
    )
    (world_dir / "stats" / f"{SILAS}.json").write_text(
        json.dumps({"stats": {"minecraft:custom": {"minecraft:deaths": 19}}, "DataVersion": 3700})
    )
    (world_dir / "advancements" / f"{JONAH}.json").write_text(
        json.dumps(
            {
                "minecraft:story/mine_stone": {"done": True},
                "minecraft:story/smelt_iron": {"done": True},
                "minecraft:nether/root": {"done": False},
                "minecraft:recipes/misc/charcoal": {"done": True},
                "DataVersion": 3700,
            }
        )
    )
    (tmp_path / "usercache.json").write_text(
        json.dumps([{"uuid": JONAH, "name": "Jonah"}, {"uuid": SILAS, "name": "Silas"}])
    )

    monkeypatch.setenv("MC_WORLD_DIR", str(world_dir))
    return world_dir


class TestReadingIsIdempotent:
    """The defect this replaces: counts that climbed on every run."""

    def test_repeated_reads_return_the_same_numbers(self, world):
        first = player_stats.read_player(JONAH)
        second = player_stats.read_player(JONAH)
        third = player_stats.read_player(JONAH)

        assert first.deaths == second.deaths == third.deaths == 7
        assert first.play_time_minutes == second.play_time_minutes == third.play_time_minutes

    def test_reading_does_not_write(self, world):
        """Nothing is accumulated, so nothing is stored"""
        before = {p: p.stat().st_mtime for p in world.rglob("*.json")}

        player_stats.read_all()
        player_stats.leaderboard("deaths")

        after = {p: p.stat().st_mtime for p in world.rglob("*.json")}
        assert before == after, "reading statistics must not touch the game's files"


class TestUnitConversions:
    """The game stores ticks, centimetres and tenths of hearts."""

    def test_play_time_is_converted_from_ticks(self, world):
        # 1,440,000 ticks / 20 per second / 60 = 1200 minutes
        assert player_stats.read_player(JONAH).play_time_minutes == 1200

    def test_distance_is_converted_from_centimetres(self, world):
        assert player_stats.read_player(JONAH).distance_walked_m == 12345

    def test_damage_is_converted_from_tenths_of_hearts(self, world):
        stats = player_stats.read_player(JONAH)
        assert stats.damage_taken == 340.0
        assert stats.damage_dealt == 990.0

    def test_half_hearts_survive_the_conversion(self, world):
        """Flooring turned 5 tenths — half a heart — into no damage at all,
        which matters most to the player who has taken the least."""
        (world / "stats" / f"{GHOST}.json").write_text(
            json.dumps(
                {
                    "stats": {
                        "minecraft:custom": {
                            "minecraft:damage_taken": 5,
                            "minecraft:damage_dealt": 3_405,
                        }
                    }
                }
            )
        )

        stats = player_stats.read_player(GHOST)

        assert stats.damage_taken == 0.5
        assert stats.damage_dealt == 340.5

    def test_the_floored_conversions_are_deliberate(self, world):
        """Play time and distance are floored on purpose; pin it so a future
        change to make them fractional is a decision rather than a drift."""
        stats = player_stats.read_player(JONAH)

        assert isinstance(stats.play_time_minutes, int)
        assert isinstance(stats.distance_walked_m, int)

    def test_the_older_play_time_key_still_works(self, world):
        """1.17 renamed play_one_minute to play_time; both are ticks"""
        (world / "stats" / f"{GHOST}.json").write_text(
            json.dumps({"stats": {"minecraft:custom": {"minecraft:play_one_minute": 72_000}}})
        )

        assert player_stats.read_player(GHOST).play_time_minutes == 60


class TestAggregates:
    def test_blocks_mined_sums_every_block_type(self, world):
        assert player_stats.read_player(JONAH).blocks_mined == 6200

    def test_advancements_exclude_recipes(self, world):
        """Recipe advancements are how recipes unlock, not achievements;
        counting them makes the number meaningless."""
        assert player_stats.read_player(JONAH).advancements == 2

    def test_a_player_with_no_advancement_file_scores_zero(self, world):
        assert player_stats.read_player(SILAS).advancements == 0

    def test_missing_counters_read_as_zero(self, world):
        """A new player's file has almost nothing in it"""
        stats = player_stats.read_player(SILAS)

        assert stats.deaths == 19
        assert stats.blocks_mined == 0
        assert stats.play_time_minutes == 0


class TestNames:
    def test_names_come_from_the_usercache(self, world):
        assert player_stats.read_player(JONAH).name == "Jonah"

    def test_lookup_by_name_is_case_insensitive(self, world):
        assert player_stats.find_by_name("jOnAh").uuid == JONAH

    def test_an_unknown_name_is_not_found(self, world):
        assert player_stats.find_by_name("Nobody") is None

    def test_an_uncached_uuid_falls_back_to_itself(self, world):
        """A player whose cache entry expired still has statistics"""
        (world / "stats" / f"{GHOST}.json").write_text(json.dumps({"stats": {}}))

        assert player_stats.read_player(GHOST).name == GHOST


class TestRobustness:
    """These files are written by a running server, so a read can land badly."""

    def test_a_truncated_file_is_skipped_not_raised(self, world):
        (world / "stats" / f"{GHOST}.json").write_text('{"stats": {"minecraft:cus')

        assert player_stats.read_player(GHOST) is None
        # And it does not take the whole listing down with it.
        assert {p.name for p in player_stats.read_all()} == {"Jonah", "Silas"}

    def test_a_missing_player_file_is_none(self, world):
        assert player_stats.read_player(GHOST) is None

    def test_a_missing_world_directory_is_empty_not_an_error(self, tmp_path, monkeypatch):
        monkeypatch.setenv("MC_WORLD_DIR", str(tmp_path / "nowhere"))

        assert player_stats.read_all() == []

    def test_a_missing_usercache_is_tolerated(self, world):
        (world.parent / "usercache.json").unlink()

        assert player_stats.read_player(JONAH).name == JONAH


class TestLeaderboard:
    def test_ranks_highest_first(self, world):
        result = player_stats.leaderboard("deaths")

        assert [e["name"] for e in result["leaderboard"]] == ["Silas", "Jonah"]
        assert result["leaderboard"][0]["value"] == 19

    def test_limit_is_respected(self, world):
        assert len(player_stats.leaderboard("deaths", limit=1)["leaderboard"]) == 1

    def test_an_unknown_metric_is_rejected(self, world):
        with pytest.raises(ValueError, match="Unknown metric"):
            player_stats.leaderboard("favourite_colour")

    @pytest.mark.parametrize(
        "legacy,resolved",
        [
            ("login_count", "play_time_minutes"),
            ("blocks_broken", "blocks_mined"),
            ("play_time", "play_time_minutes"),
        ],
    )
    def test_the_old_tracker_metric_names_still_resolve(self, world, legacy, resolved):
        """A caller using the old names gets the real counter rather than an
        empty leaderboard."""
        assert player_stats.resolve_metric(legacy) == resolved
        assert player_stats.leaderboard(legacy)["metric"] == resolved


class TestWorldResolution:
    def test_mc_world_dir_wins(self, tmp_path, monkeypatch):
        monkeypatch.setenv("MC_WORLD_DIR", str(tmp_path / "elsewhere"))

        assert player_stats.world_dir() == tmp_path / "elsewhere"

    def test_level_name_is_read_from_server_properties(self, tmp_path, monkeypatch):
        monkeypatch.delenv("MC_WORLD_DIR", raising=False)
        data = tmp_path / "data"
        data.mkdir()
        (data / "server.properties").write_text("motd=hi\nlevel-name=survival\n")
        monkeypatch.setattr(player_stats, "PROJECT_ROOT", tmp_path)

        assert player_stats.world_name() == "survival"
        assert player_stats.world_dir() == data / "survival"

    def test_the_default_is_world(self, tmp_path, monkeypatch):
        monkeypatch.delenv("MC_WORLD_DIR", raising=False)
        monkeypatch.setattr(player_stats, "PROJECT_ROOT", tmp_path)

        assert player_stats.world_name() == "world"


@pytest.fixture
def client():
    api_module.app.config["TESTING"] = True
    with api_module.app.test_client() as client:
        yield client


@pytest.fixture
def auth(monkeypatch):
    key = "player-stats-test-key"
    monkeypatch.setitem(api_module.API_KEYS, key, {"name": "t", "enabled": True, "role": "admin"})
    return {"X-API-Key": key}


class TestEndpoints:
    def test_listing_returns_every_player(self, client, auth, world):
        response = client.get("/api/players/stats", headers=auth)

        assert response.status_code == 200
        body = response.get_json()
        assert body["count"] == 2
        assert {p["name"] for p in body["players"]} == {"Jonah", "Silas"}

    def test_one_player_by_name(self, client, auth, world):
        response = client.get("/api/players/stats/Jonah", headers=auth)

        assert response.status_code == 200
        assert response.get_json()["stats"]["deaths"] == 7

    def test_raw_is_opt_in(self, client, auth, world):
        """The full stats block is large, so it is not in the default response"""
        assert "raw" not in client.get("/api/players/stats/Jonah", headers=auth).get_json()["stats"]

        detailed = client.get("/api/players/stats/Jonah?raw=true", headers=auth).get_json()
        assert "minecraft:mined" in detailed["stats"]["raw"]

    def test_an_unknown_player_is_404(self, client, auth, world):
        assert client.get("/api/players/stats/Nobody", headers=auth).status_code == 404

    def test_leaderboard_endpoint(self, client, auth, world):
        response = client.get("/api/players/stats/leaderboard?metric=deaths", headers=auth)

        assert response.status_code == 200
        assert response.get_json()["leaderboard"][0]["name"] == "Silas"

    def test_leaderboard_rejects_an_unknown_metric(self, client, auth, world):
        response = client.get("/api/players/stats/leaderboard?metric=nonsense", headers=auth)

        assert response.status_code == 400
        assert "Valid:" in response.get_json()["error"]

    def test_leaderboard_limit_is_clamped(self, client, auth, world):
        """An unbounded limit lets one request pull every player, and every
        stats file behind them. /api/deaths/leaderboard clamps the same way."""
        over = client.get("/api/players/stats/leaderboard?limit=100000", headers=auth)
        assert over.status_code == 200
        assert len(over.get_json()["leaderboard"]) <= 50

        # Zero and negative used to return nothing at all rather than being
        # treated as a mistake.
        for limit in (0, -5):
            response = client.get(f"/api/players/stats/leaderboard?limit={limit}", headers=auth)
            assert response.status_code == 200
            assert len(response.get_json()["leaderboard"]) == 1

    def test_leaderboard_rejects_a_non_numeric_limit(self, client, auth, world):
        response = client.get("/api/players/stats/leaderboard?limit=lots", headers=auth)

        assert response.status_code == 400

    def test_metrics_endpoint_lists_the_counters(self, client, auth, world):
        response = client.get("/api/players/stats/metrics", headers=auth)

        assert response.status_code == 200
        assert "blocks_mined" in response.get_json()["metrics"]

    def test_the_fixed_paths_are_not_captured_by_the_player_route(self, client, auth, world):
        """/leaderboard and /metrics must not be read as player names"""
        assert client.get("/api/players/stats/leaderboard", headers=auth).get_json().get("metric")
        assert client.get("/api/players/stats/metrics", headers=auth).get_json().get("metrics")

    def test_stats_require_authentication(self, client, world):
        assert client.get("/api/players/stats").status_code in (401, 403)

    def test_the_removed_parse_endpoint_is_gone(self, client, auth, world):
        """Nothing to parse any more; the counters are the game's own.

        405 rather than 404 because the path still matches the <player> route
        for GET — it would look for a player called "parse" — so POST is
        method-not-allowed. Either way the collection step no longer exists.
        """
        response = client.post("/api/players/stats/parse", headers=auth)

        assert response.status_code == 405
        assert "POST" not in response.headers.get("Allow", "")
