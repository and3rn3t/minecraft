"""Tests for the Pet Cemetery (api/pet_cemetery.py)."""

import json
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from api.events import GameEvent  # noqa: E402
from api.pet_cemetery import (  # noqa: E402
    CEMETERY_ORIGIN,
    CEMETERY_ROW_LENGTH,
    CEMETERY_PLOT_SPACING,
    PetCemetery,
    PetDeath,
    PetDeathRecord,
    build_gravestone_commands,
    get_cemetery,
    plot_position,
    reset_cemetery,
    write_gentle_epitaph,
)


def pet_death_event(name="Biscuit", entity_type="EntityWolf", cause="was slain by Skeleton"):
    return GameEvent(
        type="pet_death",
        timestamp="2026-09-19T12:00:00+00:00",
        player=None,
        data={"entity_type": entity_type, "name": name, "cause": cause, "log_time": "12:00:00"},
        raw=f"[12:00:00] [Server thread/INFO]: Named entity {entity_type}['{name}'/1,...] died: {name} {cause}",
    )


@pytest.fixture
def commands():
    return []


@pytest.fixture
def cemetery(tmp_path, commands):
    return PetCemetery(cemetery_dir=tmp_path / "pet_cemetery", runner=commands.append)


@pytest.fixture(autouse=True)
def clean_shared_cemetery():
    reset_cemetery()
    yield
    reset_cemetery()


@pytest.mark.unit
class TestGentleEpitaphs:
    @pytest.mark.parametrize(
        "cause",
        [
            "was slain by Skeleton",
            "blew up",
            "fell from a high place",
            "drowned",
            "burned to death",
            "tried to swim in lava",
            "was struck by lightning",
            "fell out of the world",
            "an unrecognised cause with no matching category",
        ],
    )
    def test_every_category_has_a_gentle_line(self, cause):
        death = PetDeath(entity_type="EntityWolf", name="Biscuit", cause=cause)
        epitaph = write_gentle_epitaph(death)
        assert "Biscuit" in epitaph

    def test_unrecognised_cause_falls_back_to_unknown(self):
        death = PetDeath(entity_type="EntityWolf", name="Rex", cause="did something the parser has never seen")
        epitaph = write_gentle_epitaph(death)
        assert "Rex" in epitaph

    def test_reads_gentler_than_a_player_obituary(self):
        """No jokes, no culprit-mocking -- just a name and something kind."""
        death = PetDeath(entity_type="EntityWolf", name="Biscuit", cause="was slain by Zombie")
        epitaph = write_gentle_epitaph(death)
        assert "did not come to an arrangement" not in epitaph  # a real Hall of Deaths line
        assert "could not be reached for comment" not in epitaph

    def test_stable_for_the_same_death(self):
        death = PetDeath(entity_type="EntityWolf", name="Biscuit", cause="drowned")
        assert write_gentle_epitaph(death) == write_gentle_epitaph(death)


@pytest.mark.unit
class TestSpecies:
    def test_known_entity_types_map_to_friendly_names(self):
        assert PetDeath(entity_type="EntityWolf", name="Rex", cause="drowned").species == "dog"
        assert PetDeath(entity_type="EntityCat", name="Tom", cause="drowned").species == "cat"

    def test_unknown_entity_type_falls_back_to_pet(self):
        assert PetDeath(entity_type="EntityMooshroom", name="Moo", cause="drowned").species == "pet"


@pytest.mark.unit
class TestPlots:
    def test_first_plot_is_the_origin(self):
        assert plot_position(0) == CEMETERY_ORIGIN

    def test_plots_advance_along_a_row(self):
        ox, oy, oz = CEMETERY_ORIGIN
        assert plot_position(1) == (ox + CEMETERY_PLOT_SPACING, oy, oz)

    def test_plots_wrap_to_a_new_row(self):
        ox, oy, oz = CEMETERY_ORIGIN
        assert plot_position(CEMETERY_ROW_LENGTH) == (ox, oy, oz + CEMETERY_PLOT_SPACING)

    def test_plot_numbers_persist_across_instances(self, tmp_path):
        first = PetCemetery(cemetery_dir=tmp_path / "cem")
        a = first.record(PetDeath(entity_type="EntityWolf", name="A", cause="drowned"))
        b = first.record(PetDeath(entity_type="EntityWolf", name="B", cause="drowned"))
        assert (a.plot, b.plot) == (0, 1)

        second = PetCemetery(cemetery_dir=tmp_path / "cem")
        c = second.record(PetDeath(entity_type="EntityWolf", name="C", cause="drowned"))
        assert c.plot == 2


@pytest.mark.unit
class TestGravestoneCommands:
    def test_places_a_sign_at_the_plot(self, cemetery, commands):
        cemetery.record(PetDeath(entity_type="EntityWolf", name="Biscuit", cause="drowned"))
        assert any(cmd.startswith("setblock") and "oak_sign" in cmd for cmd in commands)

    def test_quotes_in_the_name_are_escaped_not_interpolated(self):
        record = PetDeathRecord(
            name='Biscuit "the good boy"',
            species="dog",
            cause="drowned",
            category="drowning",
            epitaph="x",
            timestamp="2026-09-19T12:00:00+00:00",
            plot=0,
        )
        commands = build_gravestone_commands(record)
        sign_line = next(c for c in commands if "messages[0]" in c)
        assert '\\"the good boy\\"' in sign_line


@pytest.mark.unit
class TestRecording:
    def test_pet_death_is_recorded(self, cemetery):
        record = cemetery.handle_event(pet_death_event())
        assert record is not None
        assert record.name == "Biscuit"
        assert record.species == "dog"

    def test_non_pet_death_events_are_ignored(self, cemetery):
        event = GameEvent(type="death", timestamp="x", player="Jonah", data={"cause": "drowned"}, raw="")
        assert cemetery.handle_event(event) is None

    def test_pet_death_without_a_name_is_ignored(self, cemetery):
        event = pet_death_event(name="")
        assert cemetery.handle_event(event) is None

    def test_record_is_persisted(self, cemetery, tmp_path):
        cemetery.handle_event(pet_death_event())
        files = list((tmp_path / "pet_cemetery").glob("*.jsonl"))
        assert len(files) == 1
        stored = json.loads(files[0].read_text().splitlines()[0])
        assert stored["name"] == "Biscuit"

    def test_reading_returns_newest_first(self, cemetery):
        cemetery.record(PetDeath(entity_type="EntityWolf", name="First", cause="drowned"))
        cemetery.record(PetDeath(entity_type="EntityWolf", name="Second", cause="drowned"))
        names = [r["name"] for r in cemetery.read()]
        assert names == ["Second", "First"]


@pytest.mark.unit
class TestGravestonePlacement:
    def test_successful_placement_is_recorded(self, cemetery):
        record = cemetery.record(PetDeath(entity_type="EntityWolf", name="Biscuit", cause="drowned"))
        assert record.gravestone_placed is True

    def test_a_failed_placement_still_records_the_death(self, tmp_path):
        def failing_runner(_command):
            raise RuntimeError("server is down")

        cemetery = PetCemetery(cemetery_dir=tmp_path / "cem", runner=failing_runner)
        record = cemetery.record(PetDeath(entity_type="EntityWolf", name="Biscuit", cause="drowned"))
        assert record.gravestone_placed is False
        assert cemetery.read()[0]["name"] == "Biscuit"

    def test_no_runner_configured_is_harmless(self, tmp_path):
        cemetery = PetCemetery(cemetery_dir=tmp_path / "cem")
        record = cemetery.record(PetDeath(entity_type="EntityWolf", name="Biscuit", cause="drowned"))
        assert record.gravestone_placed is False


@pytest.mark.unit
class TestSharedCemetery:
    def test_get_cemetery_returns_a_singleton(self):
        assert get_cemetery() is get_cemetery()

    def test_reset_forces_a_rebuild(self):
        first = get_cemetery()
        reset_cemetery()
        assert get_cemetery() is not first

    def test_runner_is_attached_on_first_supply(self):
        get_cemetery()
        runner = lambda command: None  # noqa: E731
        cemetery = get_cemetery(runner=runner)
        assert cemetery.runner is runner


@pytest.mark.unit
class TestEndToEndThroughTheBus:
    def test_a_pet_death_log_line_becomes_a_gravestone(self, tmp_path, commands):
        from api.events import EventBus

        cemetery = PetCemetery(cemetery_dir=tmp_path / "cem", runner=commands.append)
        bus = EventBus(events_dir=tmp_path / "events", flush_every_events=1)
        bus.subscribe(cemetery.handle_event)

        line = (
            "[12:00:00] [Server thread/INFO]: Named entity EntityWolf['Biscuit'/1, uuid='x', "
            "l='ServerLevel[minecraft:overworld]', x=0, y=0, z=0, cpos=[0,0], tl=1, v=true, rR=null] "
            "died: Biscuit was slain by Skeleton"
        )
        bus.handle_line(line)

        records = cemetery.read()
        assert len(records) == 1
        assert records[0]["name"] == "Biscuit"
        assert any("oak_sign" in c for c in commands)
