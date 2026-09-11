from __future__ import annotations

from tangl.core import DispatchLayer
from tangl.persistence.factory import PersistenceManagerFactory
from tangl.presentation.dispatch import presentation_dispatch
from tangl.presentation.projection import (
    InfoAffordance,
    KvListValue,
    ProjectionRequest,
    ProjectedSection,
)
from tangl.presentation.values import KvRow
from tangl.service import build_service_manager
from tangl.service.dispatch import do_get_story_info, service_dispatch
from tangl.service.user.user import User
from tangl.story import InitMode, World


def _script() -> dict[str, object]:
    return {
        "label": "story_info_world",
        "metadata": {"title": "Story Info", "author": "Tests", "start_at": "intro.start"},
        "scenes": {"intro": {"blocks": {"start": {"content": "Start"}}}},
    }


def _section(label: str) -> ProjectedSection:
    return ProjectedSection(
        section_id=label,
        title=label.title(),
        kind="proof",
        value=KvListValue(items=[KvRow(key="Source", value=label)]),
    )


def test_service_story_info_uses_private_session_fallback() -> None:
    World.clear_instances()
    try:
        persistence = PersistenceManagerFactory.create_persistence_manager(
            manager_name="json_sqlite_in_mem",
        )
        manager = build_service_manager(persistence)
        user = User(label="story-info-fallback-user")
        persistence.save(user)
        world = World.from_script_data(script_data=_script())
        manager.create_story(
            user_id=user.uid,
            world_id=world.label,
            world=world,
            init_mode=InitMode.EAGER.value,
            story_label="story-info-fallback-story",
        )

        catalog = manager.get_story_info(user_id=user.uid)
        state = manager.get_story_info(user_id=user.uid, channels=["ui-sidebar"])

        assert [channel.channel_id for channel in catalog.channels] == ["ui-sidebar"]
        assert [section.section_id for section in state.sections] == ["session"]
        assert [item.key for item in state.sections[0].value.items] == [
            "Cursor",
            "Step",
            "Turn",
            "Journal size",
        ]
    finally:
        World.clear_instances()


def test_service_dispatch_composes_service_presentation_world_and_runtime_contributors() -> None:
    World.clear_instances()
    try:
        persistence = PersistenceManagerFactory.create_persistence_manager(
            manager_name="json_sqlite_in_mem",
        )
        manager = build_service_manager(persistence)
        user = User(label="story-info-dispatch-user")
        persistence.save(user)
        world = World.from_script_data(
            script_data={**_script(), "label": "story_info_dispatch_world"},
        )

        def advertise_rules(*, caller: object, **_kw: object) -> InfoAffordance:
            return InfoAffordance(channel_id="ui-proof", label="Proof")

        def service_provider(*, caller: object, **_kw: object) -> ProjectedSection:
            return _section("service")

        def presentation_provider(*, caller: object, **_kw: object) -> ProjectedSection:
            return _section("presentation")

        def world_provider(*, caller: object, **_kw: object) -> ProjectedSection:
            return _section("world")

        def runtime_provider(*, caller: object, **_kw: object) -> ProjectedSection:
            return _section("runtime")

        world.dispatch.register(advertise_rules, task="advertise_info_channels")
        service_dispatch.register(service_provider, task="get_story_info")
        presentation_dispatch.register(presentation_provider, task="get_story_info")
        world.dispatch.register(
            world_provider,
            task="get_story_info",
            dispatch_layer=DispatchLayer.AUTHOR,
        )

        manager.create_story(
            user_id=user.uid,
            world_id=world.label,
            world=world,
            init_mode=InitMode.EAGER.value,
            story_label="story_info_dispatch_story",
        )
        with manager.open_session(user_id=user.uid, write_back=False) as session:
            session.ledger.local_behaviors.register(
                runtime_provider,
                task="get_story_info",
                dispatch_layer=DispatchLayer.LOCAL,
            )
            state = do_get_story_info(
                session.ledger.cursor,
                ctx=manager._make_story_info_ctx(session.ledger),
                request=ProjectionRequest(channels=["ui-proof"]),
            )

        assert [section.section_id for section in state.sections] == [
            "service",
            "presentation",
            "world",
            "runtime",
        ]
    finally:
        World.clear_instances()
