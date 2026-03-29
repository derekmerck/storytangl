from __future__ import annotations

from types import SimpleNamespace

from tangl.core import Graph
from tangl.persistence.factory import PersistenceManagerFactory
from tangl.service import build_service_manager
from tangl.service.response import KvListValue, ProjectedKVItem, ProjectedSection, ProjectedState
from tangl.service.story_info import (
    DEFAULT_STORY_INFO_PROJECTOR,
    DefaultStoryInfoProjector,
    resolve_story_info_projector,
)
from tangl.service.user.user import User
from tangl.story import InitMode, World
from tangl.vm.runtime.ledger import Ledger


def _script() -> dict[str, object]:
    return {
        "label": "story_info_world",
        "metadata": {"title": "Story Info", "author": "Tests", "start_at": "intro.start"},
        "scenes": {
            "intro": {
                "blocks": {
                    "start": {
                        "content": "Start",
                    }
                }
            }
        },
    }


def _custom_state(*, title: str, label: str) -> ProjectedState:
    return ProjectedState(
        sections=[
            ProjectedSection(
                section_id="custom",
                title=title,
                kind="mystery",
                value=KvListValue(items=[ProjectedKVItem(key="Label", value=label)]),
            )
        ]
    )


class _Projector:
    def __init__(self, state: ProjectedState) -> None:
        self.state = state

    def project(self, *, ledger: Ledger) -> ProjectedState:
        return self.state


def _make_ledger() -> Ledger:
    graph = Graph()
    start = graph.add_node(label="start")
    return Ledger.from_graph(graph=graph, entry_id=start.uid)


def test_resolve_story_info_projector_prefers_world_override() -> None:
    world_projector = _Projector(_custom_state(title="World State", label="world"))
    domain_projector = _Projector(_custom_state(title="Domain State", label="domain"))
    world = World.from_script_data(
        script_data=_script(),
        domain=SimpleNamespace(get_story_info_projector=lambda: domain_projector),
        story_info_projector=world_projector,
    )

    ledger = _make_ledger()
    ledger.graph = SimpleNamespace(world=world)

    projector = resolve_story_info_projector(ledger)
    assert projector is world_projector
    assert projector.project(ledger=ledger).sections[0].title == "World State"


def test_resolve_story_info_projector_falls_back_to_domain_projector() -> None:
    domain_projector = _Projector(_custom_state(title="Domain State", label="domain"))
    world = World.from_script_data(
        script_data=_script(),
        domain=SimpleNamespace(get_story_info_projector=lambda: domain_projector),
    )

    ledger = _make_ledger()
    ledger.graph = SimpleNamespace(world=world)

    projector = resolve_story_info_projector(ledger)
    assert projector is domain_projector
    assert projector.project(ledger=ledger).sections[0].title == "Domain State"


def test_default_story_info_projector_returns_minimal_session_section() -> None:
    ledger = _make_ledger()

    projector = resolve_story_info_projector(ledger)
    state = projector.project(ledger=ledger)

    assert projector is DEFAULT_STORY_INFO_PROJECTOR
    assert isinstance(projector, DefaultStoryInfoProjector)
    assert state.sections[0].section_id == "session"
    items = state.sections[0].value.items
    assert [item.key for item in items] == ["Cursor", "Step", "Turn", "Journal size"]


def test_default_story_info_projector_handles_ledger_without_graph_binding() -> None:
    ledger = _make_ledger()
    ledger.graph = None

    state = resolve_story_info_projector(ledger).project(ledger=ledger)

    items = state.sections[0].value.items
    assert [item.key for item in items] == ["Step", "Turn", "Journal size"]


def test_story_info_keeps_world_projector_after_structured_persistence_roundtrip() -> None:
    World.clear_instances()
    try:
        persistence = PersistenceManagerFactory.create_persistence_manager(
            manager_name="json_sqlite_in_mem",
        )
        manager = build_service_manager(persistence)

        user = User(label="story-info-structured-user")
        persistence.save(user)

        world = World.from_script_data(
            script_data={**_script(), "label": "story_info_structured_world"},
            story_info_projector=_Projector(
                _custom_state(title="World State", label="world"),
            ),
        )

        created = manager.create_story(
            user_id=user.uid,
            world_id=world.label,
            world=world,
            init_mode=InitMode.EAGER.value,
            story_label="story_info_structured_story",
        )
        assert created.metadata["world_id"] == world.label

        fresh_manager = build_service_manager(persistence)
        info = fresh_manager.get_story_info(
            user_id=user.uid,
        )

        assert isinstance(info, ProjectedState)
        assert info.sections[0].section_id == "custom"
        assert info.sections[0].title == "World State"
    finally:
        World.clear_instances()
