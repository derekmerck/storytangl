"""Phase 1 spike: the Player concept and its world-local Regent composition.

Validates two things before any content is authored:

1. ``Player`` publishes itself into the namespace via the existing
   ``@contribute_ns`` mechanism and its unified ``has()`` activator query is
   readable from an authored ``Predicate`` (the gating/activator surface).
2. ``Regent(Player, HasStats, HasWallet)`` -- a story concept composed with
   progression mechanics mixins -- has a sane MRO and round-trips through the
   polymorphic ``unstructure()``/``structure()`` serialization contract.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from tangl.core.runtime_op import Predicate
from tangl.story import Player


class TestPlayerConcept:
    def test_publishes_self_and_state_into_namespace(self) -> None:
        player = Player(full_name="Elodie", mood="willful")
        player.flags.add("impressed_prince")

        ns = dict(player.get_ns())

        assert ns["player"] is player
        assert ns["mood"] == "willful"
        assert "impressed_prince" in ns["flags"]

    def test_has_matches_tags_inv_flags_and_achievements(self) -> None:
        player = Player()
        player.inv.add("dragonslayer_sword")
        player.flags.add("irritated_dragon")
        player.achievements.add("first_blood")

        assert player.has("dragonslayer_sword")
        assert player.has("irritated_dragon")
        assert player.has("first_blood")
        assert player.has("dragonslayer_sword", "irritated_dragon")
        assert not player.has("crown")

    def test_has_is_readable_from_an_authored_predicate(self) -> None:
        """The activator path: a `conditions:`-style predicate over the ns."""
        player = Player()
        gate = Predicate(expr="player.has('student_outfit')")

        ns = dict(player.get_ns())
        assert gate.satisfied_by(ns) is False

        player.inv.add("student_outfit")
        ns = dict(player.get_ns())
        assert gate.satisfied_by(ns) is True


def _load_regent_cls():
    """Import the world-local Regent the way the bundle exposes it."""
    pkg_root = (
        Path(__file__).resolve().parents[3]
        / "worlds"
        / "coronate_the_regent"
    )
    if str(pkg_root) not in sys.path:
        sys.path.insert(0, str(pkg_root))
    from coronate_the_regent.domain import Regent

    return Regent


class TestRegentComposition:
    def test_mro_includes_story_player_and_progression_mixins(self) -> None:
        Regent = _load_regent_cls()
        mro_names = [cls.__name__ for cls in Regent.__mro__]

        assert mro_names[0] == "Regent"
        for expected in ("Player", "HasStats", "HasWallet", "Node", "Entity"):
            assert expected in mro_names, f"{expected} missing from MRO: {mro_names}"

    def test_constructs_with_seed_stats_and_wallet(self) -> None:
        Regent = _load_regent_cls()
        regent = Regent(full_name="Elodie")

        # Stats come from the seed system; competency math is reusable.
        assert {"body", "mind", "spirit", "combat", "magic", "charm"} <= set(
            regent.stats
        )
        assert regent.wallet["coin"] == 3
        assert regent.can_afford({"coin": 2})

        # Player behavior survives composition.
        regent.flags.add("impressed_prince")
        assert regent.has("impressed_prince")
        assert dict(regent.get_ns())["player"] is regent

    def test_round_trips_through_unstructure_structure(self) -> None:
        Regent = _load_regent_cls()
        regent = Regent(full_name="Elodie", mood="afraid")
        regent.inv.add("dragonslayer_sword")
        regent.flags.add("irritated_dragon")
        regent.wallet["coin"] = 7

        restored = type(regent).structure(regent.unstructure())

        assert restored.uid == regent.uid
        assert restored.full_name == "Elodie"
        assert restored.mood == "afraid"
        assert restored.has("dragonslayer_sword", "irritated_dragon")
        assert restored.wallet["coin"] == 7
        assert set(restored.stats) == set(regent.stats)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-q"]))
