"""Contract tests for on-node narrator knowledge on story concepts."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Callable, Iterator

from tangl.core import Graph, Selector
from tangl.story.concepts import Actor, EntityKnowledge, Location, Role, Setting, get_narrator_key
from tangl.vm import Requirement
from tangl.vm.dispatch import dispatch as vm_dispatch, on_journal
from tangl.vm.replay import Patch, OpEnum
from tangl.vm.runtime.ledger import Ledger
from tangl.vm.traversable import TraversableEdge


def _make_role() -> Role:
    return Role(
        label="villain",
        requirement=Requirement(has_kind=Actor, hard_requirement=False),
    )


def _make_setting() -> Setting:
    return Setting(
        label="place",
        requirement=Requirement(has_kind=Location, hard_requirement=False),
    )


@contextmanager
def _cleanup_behaviors(*funcs: Callable[..., object]) -> Iterator[None]:
    try:
        yield
    finally:
        for func in funcs:
            behavior = getattr(func, "_behavior", None)
            if behavior is not None:
                vm_dispatch.remove(behavior.uid)


def test_story_concepts_expose_lazy_default_knowledge() -> None:
    concepts = [
        Actor(label="katya", name="Katya"),
        Location(label="bar", name="Blue Moon"),
        _make_role(),
        _make_setting(),
    ]

    for concept in concepts:
        knowledge = concept.get_knowledge()
        assert isinstance(knowledge, EntityKnowledge)
        assert knowledge.state == "UNKNOWN"
        assert knowledge is concept.get_knowledge()
        assert concept.narrator_knowledge["_"] is knowledge


def test_story_concepts_isolate_multiple_narrator_keys() -> None:
    actor = Actor(label="katya", name="Katya")

    actor.get_knowledge("player").state = "IDENTIFIED"
    actor.get_knowledge("guide").state = "FAMILIAR"

    assert actor.get_knowledge("player").state == "IDENTIFIED"
    assert actor.get_knowledge("guide").state == "FAMILIAR"
    assert actor.get_knowledge().state == "UNKNOWN"


def test_story_concepts_roundtrip_narrator_knowledge_through_constructor_form() -> None:
    concepts = [
        Actor(label="katya", name="Katya"),
        Location(label="bar", name="Blue Moon"),
        _make_role(),
        _make_setting(),
    ]

    for concept in concepts:
        concept.get_knowledge("player").state = "IDENTIFIED"
        concept.get_knowledge("player").identification_source = "test"
        payload = concept.unstructure()
        restored = type(concept).structure(payload)

        assert restored.get_knowledge("player").state == "IDENTIFIED"
        assert restored.get_knowledge("player").identification_source == "test"


def test_get_narrator_key_reads_context_meta_with_default_fallback() -> None:
    class _Ctx:
        def __init__(self, narrator_key: str | None = None) -> None:
            self._meta = {"narrator_key": narrator_key} if narrator_key is not None else {}

        def get_meta(self):
            return dict(self._meta)

    assert get_narrator_key(_Ctx("guide")) == "guide"
    assert get_narrator_key(_Ctx()) == "_"
    assert get_narrator_key(None) == "_"


def test_narrator_knowledge_updates_participate_in_patch_and_rollback() -> None:
    graph = Graph()
    origin = Location(label="origin", name="Origin")
    destination = Location(label="harbor", name="Harbor")
    graph.add(origin)
    graph.add(destination)
    edge = TraversableEdge(predecessor_id=origin.uid, successor_id=destination.uid)
    graph.add(edge)

    @on_journal
    def identify_location(*, caller, ctx, **_kw):
        if caller is destination:
            knowledge = caller.get_knowledge("player")
            knowledge.state = "IDENTIFIED"
            knowledge.identification_source = "journal_test"
        return None

    with _cleanup_behaviors(identify_location):
        ledger = Ledger.from_graph(graph=graph, entry_id=origin.uid)
        ledger.resolve_choice(edge.uid)

        assert destination.get_knowledge("player").state == "IDENTIFIED"

        patches = list(Selector(has_kind=Patch).filter(ledger.output_stream))
        assert patches
        assert any(
            event.operation is OpEnum.UPDATE
            and event.item_id == destination.uid
            and isinstance(event.value, dict)
            and event.value.get("narrator_knowledge", {})
            .get("player", {})
            .get("state")
            == "IDENTIFIED"
            for patch in patches
            for event in patch.events
        )

        ledger.rollback_to_step(0, reason="reset narrator knowledge")
        restored = ledger.graph.get(destination.uid)
        assert restored.get_knowledge("player").state == "UNKNOWN"
