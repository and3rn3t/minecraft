"""Tests for epitaph writing (api/epitaphs.py)."""

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from api.epitaphs import (  # noqa: E402
    Death,
    TemplateEpitaphWriter,
    classify_cause,
    extract_culprit,
    write_epitaph,
)


@pytest.mark.unit
class TestClassification:
    @pytest.mark.parametrize(
        "cause,expected",
        [
            ("was slain by Zombie", "combat"),
            ("was shot by Skeleton", "combat"),
            ("was fireballed by Ghast", "combat"),
            ("was stung to death by Bee", "combat"),
            ("blew up", "explosion"),
            ("was blown up by Creeper", "explosion"),
            ("went off with a bang", "explosion"),
            ("tried to swim in lava", "lava"),
            ("discovered the floor was lava", "lava"),
            ("went up in flames", "fire"),
            ("burned to death", "fire"),
            ("fell from a high place", "fall"),
            ("hit the ground too hard", "fall"),
            ("fell off scaffolding", "fall"),
            ("drowned", "drowning"),
            ("starved to death", "starvation"),
            ("died from dehydration", "dehydration"),
            ("fell out of the world", "void"),
            ("froze to death", "freezing"),
            ("was struck by lightning", "lightning"),
            ("suffocated in a wall", "crushing"),
            ("was squashed by a falling anvil", "crushing"),
            ("was impaled on a stalagmite", "spikes"),
            ("was poked to death by a sweet berry bush", "prickly"),
            ("walked into a cactus while trying to escape Zombie", "prickly"),
            ("withered away", "magic"),
            ("was killed by magic", "magic"),
            ("experienced kinetic energy", "kinetic"),
            ("was obliterated by a sonically-charged shriek", "sonic"),
        ],
    )
    def test_causes_map_to_categories(self, cause, expected):
        assert classify_cause(cause) == expected

    def test_explosion_beats_combat(self):
        """'was blown up by Creeper' matches both forms; the specific one wins."""
        assert classify_cause("was blown up by Creeper") == "explosion"

    def test_prickly_beats_combat_when_fleeing(self):
        """A cactus death names a mob but is not a mob kill."""
        assert classify_cause("walked into a cactus while trying to escape Creeper") == "prickly"

    def test_unrecognised_cause_is_unknown(self):
        assert classify_cause("was gently disapproved of") == "unknown"

    def test_empty_cause_is_unknown(self):
        assert classify_cause("") == "unknown"
        assert classify_cause(None) == "unknown"


@pytest.mark.unit
class TestCulpritExtraction:
    def test_simple_killer(self):
        assert extract_culprit("was slain by Zombie") == "Zombie"

    def test_weapon_is_dropped(self):
        """The epitaphs read better naming the culprit alone."""
        assert extract_culprit("was slain by Silas using Netherite Sword") == "Silas"

    def test_projectile_killer(self):
        assert extract_culprit("was shot by Skeleton") == "Skeleton"

    def test_definite_article_is_dropped(self):
        assert extract_culprit("was slain by the Warden") == "Warden"

    def test_causeless_death_has_no_culprit(self):
        assert extract_culprit("fell from a high place") is None
        assert extract_culprit("drowned") is None

    def test_empty_cause(self):
        assert extract_culprit("") is None


@pytest.mark.unit
class TestEpitaphWriting:
    def test_every_category_has_epitaphs(self):
        """A category with no templates would fall through to 'unknown'."""
        from api.epitaphs import _CAUSE_PATTERNS, _EPITAPHS

        for category, _pattern in _CAUSE_PATTERNS:
            assert category in _EPITAPHS, f"no epitaphs for {category}"
            assert _EPITAPHS[category], f"empty epitaph list for {category}"

    def test_player_name_appears(self):
        death = Death(player="Jonah", cause="drowned", timestamp="t")
        assert "Jonah" in write_epitaph(death)

    def test_culprit_appears_in_combat_epitaphs(self):
        death = Death(player="Silas", cause="was slain by Creeper", timestamp="t")
        epitaph = write_epitaph(death)
        assert "Silas" in epitaph
        assert "Creeper" in epitaph

    def test_combat_without_a_named_culprit_still_reads(self):
        """Some combat phrasings name nobody; the line must not say 'None'."""
        death = Death(player="Jonah", cause="was killed trying to hurt something", timestamp="t")
        epitaph = write_epitaph(death)
        assert "None" not in epitaph
        assert "{" not in epitaph

    def test_no_placeholder_survives_for_any_category(self):
        """An unsubstituted {culprit} would show up verbatim in chat."""
        causes = [
            "was slain by Zombie",
            "blew up",
            "fell from a high place",
            "drowned",
            "starved to death",
            "froze to death",
            "was struck by lightning",
            "withered away",
            "something unrecognised",
        ]
        for index, cause in enumerate(causes):
            epitaph = write_epitaph(Death(player="Jonah", cause=cause, timestamp=f"t{index}"))
            assert "{" not in epitaph and "}" not in epitaph, cause

    def test_same_death_always_gets_the_same_epitaph(self):
        """Stable output keeps a regenerated record from changing under you."""
        death = Death(player="Jonah", cause="drowned", timestamp="2026-01-01T00:00:00+00:00")
        first = write_epitaph(death)
        second = write_epitaph(death)
        assert first == second

    def test_different_deaths_vary(self):
        """Ten identical deaths should not read identically all evening."""
        epitaphs = {
            write_epitaph(Death(player="Jonah", cause="fell from a high place", timestamp=f"t{i}")) for i in range(25)
        }
        assert len(epitaphs) > 1

    def test_unknown_cause_gets_a_noncommittal_line(self):
        death = Death(player="Silas", cause="was mildly inconvenienced", timestamp="t")
        assert "Silas" in write_epitaph(death)

    def test_writer_can_be_swapped(self):
        """The seam a language-model-backed writer would use."""

        class ShoutyWriter:
            def write(self, death):
                return f"{death.player} IS NO MORE"

        death = Death(player="Jonah", cause="drowned", timestamp="t")
        assert write_epitaph(death, ShoutyWriter()) == "Jonah IS NO MORE"

    def test_template_writer_is_the_default(self):
        death = Death(player="Jonah", cause="drowned", timestamp="t")
        expected = TemplateEpitaphWriter().write(death)
        assert write_epitaph(death) == expected


@pytest.mark.unit
class TestDeathProperties:
    def test_category_and_culprit_are_derived(self):
        death = Death(player="Jonah", cause="was slain by Zombie")
        assert death.category == "combat"
        assert death.culprit == "Zombie"
