"""A block's surface is stored as data, not as a reference to a class.

Issue #449 asks that a changed qualified class reference be treated as a
persistence decision rather than a mechanical inconvenience, which is the right
instinct: several models in this graph *do* serialize a dotted path, so moving
one of those between packages would strand every stored graph naming it.

The surface is not one of them. It rides its block as an ordinary nested value
and comes back as plain fields, so relocating the module -- as slice 3 did, from
``tangl.mechanics.surface`` to ``tangl.presentation.surface`` -- costs no
migration. That is a property worth pinning rather than re-deriving the next
time the package boundary moves, and it is the thing that would actually break:
not the round trip, but the path baked into it.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from tangl.core import Graph
from tangl.loaders import WorldBundle
from tangl.loaders.compiler import WorldCompiler
from tangl.presentation.surface import Surface
from tangl.story import InitMode

WORLDS = Path(__file__).resolve().parents[3] / "worlds"


@pytest.fixture
def graph():
    # Function-scoped: the suite clears world registries between tests, and
    # ``Graph.structure`` needs the domain classes still resolvable.
    world = WorldCompiler().compile(WorldBundle.load(WORLDS / "hall_monitor"))
    return world.create_story("surface_wire", init_mode=InitMode.EAGER).graph


def _surfaced(graph):
    return [node for node in graph.nodes if isinstance(getattr(node, "surface", None), Surface)]


def test_a_surface_survives_a_graph_round_trip(graph) -> None:
    before = _surfaced(graph)
    assert [node.label for node in before] == ["morning_shift"]

    after = _surfaced(Graph.structure(graph.unstructure()))

    assert after[0].surface.model_dump() == before[0].surface.model_dump()


def test_slot_order_survives_a_graph_round_trip(graph) -> None:
    """Authored order decides which of two same-kind slots a piece lands in.

    A round trip through a mapping that did not preserve insertion order would
    reorder the desk without changing any value, so equality of the dumps alone
    would not catch it.
    """

    before = _surfaced(graph)[0].surface
    after = _surfaced(Graph.structure(graph.unstructure()))[0].surface

    assert list(after.slots) == list(before.slots)
    assert list(after.slots) == ["student", "pass_id", "note", "permit"]


def test_the_stored_surface_names_no_class_path(graph) -> None:
    """So the module may move without a data migration.

    Asserted against the whole payload rather than the surface's own subtree,
    because a qualified reference could be recorded by whatever embeds it rather
    than by the value itself. Other models in this same payload do carry dotted
    paths, which is what makes the absence meaningful instead of vacuous.
    """

    blob = json.dumps(graph.unstructure(), default=str)

    assert "mechanics.surface" not in blob
    assert "presentation.surface" not in blob
    # The payload really does record class paths for other models, so the
    # assertions above are not passing merely because nothing is qualified.
    assert re.search(r"tangl\.story\.episode\.block\.Block", blob)
