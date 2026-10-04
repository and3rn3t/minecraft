"""Every API module derives PROJECT_ROOT from its own file, so it must be a clean absolute path.

pytest's `pythonpath = ../..` puts an unnormalised entry (".../tests/api/../..") on sys.path.
A module imported through it used to get a PROJECT_ROOT containing "..", which made the file
browser's `relative_to(PROJECT_ROOT)` raise ValueError and answer 500 for any path under it.
"""

import importlib

import pytest

MODULES = ["rcon", "server", "pet_cemetery", "bedtime", "events", "hall_of_deaths", "player_stats", "oracle"]


@pytest.mark.parametrize("name", MODULES)
def test_project_root_is_resolved(name):
    root = importlib.import_module(f"api.{name}").PROJECT_ROOT

    assert root.is_absolute()
    assert ".." not in root.parts
    assert root == root.resolve()
