#!/usr/bin/env python3
"""Epitaph writing for the Hall of Deaths.

Turns a death event into a one-line obituary in the voice of a Victorian
newspaper. Deaths are the most reliably funny thing that happens on a survival
server, and a death message that reads like a broadsheet notice is funnier than
one that reads like a log line.

Writing is behind a small interface so the source of the text can change without
anything else moving. :class:`TemplateEpitaphWriter` is the default: it runs
offline, costs nothing, returns instantly and needs no API key, which makes it
the right thing to have on a Raspberry Pi in a family's house. A writer backed
by a language model can be dropped in later by implementing ``write()``.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Optional, Protocol

# Cause categories, in the order they are tested. Order matters: several phrases
# overlap, and the more specific pattern has to win. "was blown up by" must be
# matched as an explosion before the generic "was ... by" combat form.
_CAUSE_PATTERNS: tuple[tuple[str, str], ...] = (
    ("explosion", r"blew up|was blown up by|went off with a bang"),
    ("lava", r"tried to swim in lava|discovered the floor was lava"),
    ("fire", r"went up in flames|burned to death|was burnt to a crisp"),
    ("lightning", r"was struck by lightning"),
    ("freezing", r"froze to death|was frozen to death"),
    ("drowning", r"^drowned"),
    ("dehydration", r"died from dehydration"),
    ("starvation", r"starved to death"),
    ("void", r"fell out of the world|left the confines of this world|didn't want to live"),
    ("fall", r"fell from a high place|hit the ground too hard|fell off|fell while climbing|was doomed to fall"),
    ("kinetic", r"experienced kinetic energy"),
    ("spikes", r"was impaled on a stalagmite|was skewered by a falling stalactite"),
    ("crushing", r"suffocated in a wall|was squished too much|was squashed by"),
    ("prickly", r"was pricked to death|walked into a cactus|was poked to death by a sweet berry bush"),
    ("magic", r"was killed by magic|withered away|was killed by even more magic"),
    ("sonic", r"was obliterated by a sonically-charged shriek|was roared at by"),
    ("combat", r"was slain by|was shot by|was fireballed by|was stung to death|was pummeled by|was killed by"),
    ("combat", r"was impaled by|was skewered by|got finished off by|was killed trying to hurt"),
)

_COMPILED_PATTERNS = tuple((category, re.compile(pattern)) for category, pattern in _CAUSE_PATTERNS)

# Who or what did it, for the causes that name a culprit.
_CULPRIT_RE = re.compile(
    r"(?:was (?:slain|shot|killed|fireballed|stung to death|pummeled|impaled|skewered|blown up|frozen to death)"
    r"|got finished off) by (?:the )?(?P<culprit>[^,]+?)(?: using .+)?$"
)

# One line each, with {player} and sometimes {culprit} substituted. Several per
# category so the same death does not read the same way twice in an evening.
_EPITAPHS: dict[str, tuple[str, ...]] = {
    "combat": (
        "{player}, cut down in their prime by {culprit}. The {culprit} could not be reached for comment.",
        "Here lies {player}, who met {culprit} and did not come to an arrangement.",
        "{player} is survived by their inventory. {culprit} is survived by everything else.",
        "A brief but memorable disagreement between {player} and {culprit} has been settled.",
        "{player} approached {culprit} with confidence, and departed without it.",
    ),
    "explosion": (
        "{player} has been distributed widely across the landscape.",
        "Here lies {player}, and over there, and a bit further along as well.",
        "{player} discovered that some things should not be stood next to.",
        "We gather to remember {player}, whose final moment was admittedly spectacular.",
        "{player} went out with a bang, as they had always quietly hoped to.",
    ),
    "lava": (
        "{player} tested the lava. The lava tested back, and won.",
        "Here lies {player}, briefly. Very briefly.",
        "{player} is remembered fondly, if not recoverably.",
        "The estate of {player} regrets that nothing could be retrieved.",
    ),
    "fire": (
        "{player} burned brightly, then not at all.",
        "Here lies {player}, who was warned about the fire and chose otherwise.",
        "{player} has gone out. We are all a little colder for it.",
    ),
    "fall": (
        "{player} fell a great distance, and arrived all at once.",
        "Here lies {player}, who had a wonderful view right up until the end.",
        "{player} descended with enthusiasm and landed with finality.",
        "The ground has issued a statement regarding {player}. It is unrepentant.",
        "{player} discovered that gravity keeps very careful accounts.",
    ),
    "void": (
        "{player} left this world entirely, and did not leave a note.",
        "Here lies {player}, nowhere in particular.",
        "{player} has gone somewhere we cannot follow, and frankly would not wish to.",
    ),
    "drowning": (
        "{player} ran out of air, and then out of options.",
        "Here lies {player}, who was so nearly at the surface.",
        "{player} is survived by a great many fish, all of whom seem fine.",
    ),
    "starvation": (
        "{player} had many talents. Packing snacks was not among them.",
        "Here lies {player}, who meant to eat something about an hour ago.",
        "{player} is survived by an empty inventory and an emptier stomach.",
    ),
    "dehydration": (
        "{player} went without water for rather too long.",
        "Here lies {player}, parched and unrepentant.",
    ),
    "freezing": (
        "{player} has been preserved beautifully, and permanently.",
        "Here lies {player}, who underestimated the weather.",
        "{player} is cold. {player} will remain cold.",
    ),
    "lightning": (
        "{player} was selected personally by the sky.",
        "Here lies {player}, struck by fortune of the very worst sort.",
        "The heavens have made their position on {player} abundantly clear.",
    ),
    "crushing": (
        "{player} was compressed into a smaller {player}.",
        "Here lies {player}, rather more flatly than intended.",
        "{player} occupied a space that something heavier had already claimed.",
    ),
    "spikes": (
        "{player} was arranged neatly onto something sharp.",
        "Here lies {player}, who found the pointy end.",
    ),
    "prickly": (
        "{player} was defeated by a plant. A small one.",
        "Here lies {player}, undone by shrubbery.",
        "{player} lost an argument with foliage and did not take it well.",
    ),
    "magic": (
        "{player} was unmade by forces they did not consent to.",
        "Here lies {player}, withered and bewildered in equal measure.",
        "Something unspeakable happened to {player}. We shall not speak of it.",
    ),
    "sonic": (
        "{player} was shouted at, conclusively.",
        "Here lies {player}, who should have stayed quiet.",
    ),
    "kinetic": (
        "{player} converted a great deal of speed into a very small amount of wall.",
        "Here lies {player}, who flew beautifully and stopped abruptly.",
    ),
    "unknown": (
        "{player} has died. The circumstances remain under investigation.",
        "Here lies {player}, in a manner the record does not adequately explain.",
        "{player} is no longer with us. Nobody is quite sure why.",
    ),
}

# Used when a combat template needs a culprit but none could be parsed.
_UNKNOWN_CULPRIT = "person or persons unknown"


@dataclass(frozen=True)
class Death:
    """The facts of one death, as the epitaph writer needs them."""

    player: str
    cause: str
    message: str = ""
    timestamp: str = ""

    @property
    def category(self) -> str:
        """Which kind of death this was, for choosing a set of epitaphs."""
        return classify_cause(self.cause)

    @property
    def culprit(self) -> Optional[str]:
        """Who or what did it, when the message names one."""
        return extract_culprit(self.cause)


def classify_cause(cause: str) -> str:
    """Map a vanilla death cause to an epitaph category.

    Returns ``"unknown"`` for anything unrecognised, which has its own
    deliberately noncommittal epitaphs rather than a wrong-sounding guess.
    """
    if not cause:
        return "unknown"

    text = cause.strip().lower()
    for category, pattern in _COMPILED_PATTERNS:
        if pattern.search(text):
            return category
    return "unknown"


def extract_culprit(cause: str) -> Optional[str]:
    """Pull the killer's name out of a death cause, if it names one.

    ``"was slain by Zombie using Iron Sword"`` yields ``"Zombie"``. The weapon
    is dropped: the epitaphs read better naming the culprit alone.
    """
    if not cause:
        return None
    match = _CULPRIT_RE.search(cause.strip())
    if not match:
        return None
    culprit = match.group("culprit").strip()
    return culprit or None


def _choose(options: tuple[str, ...], seed: str) -> str:
    """Pick one option, stably for a given seed.

    Hashing rather than ``random`` keeps a death's epitaph identical if it is
    ever regenerated, and keeps the tests deterministic without pinning a seed.
    """
    digest = hashlib.sha256(seed.encode("utf-8")).digest()
    return options[int.from_bytes(digest[:4], "big") % len(options)]


class EpitaphWriter(Protocol):
    """Anything that can turn a death into a line of prose."""

    def write(self, death: Death) -> str:  # pragma: no cover - interface only
        """Return a one-line epitaph for this death."""


class TemplateEpitaphWriter:
    """Writes epitaphs from built-in templates.

    Offline, free and instant. This is the default because the server runs in a
    family's house on a Pi, where a per-death network call to a paid API is a
    poor trade for a joke that a template tells just as well.
    """

    def write(self, death: Death) -> str:
        category = death.category
        options = _EPITAPHS.get(category, _EPITAPHS["unknown"])

        # The seed includes the timestamp so two identical deaths by the same
        # player still read differently.
        template = _choose(options, f"{death.player}|{death.cause}|{death.timestamp}")

        culprit = death.culprit or _UNKNOWN_CULPRIT
        return template.format(player=death.player, culprit=culprit)


_default_writer = TemplateEpitaphWriter()


def write_epitaph(death: Death, writer: Optional[EpitaphWriter] = None) -> str:
    """Write an epitaph for a death, using the default writer unless told otherwise."""
    return (writer or _default_writer).write(death)
