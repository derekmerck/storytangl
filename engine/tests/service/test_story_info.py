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


def test_public_world_media_uses_inventory_and_normal_delivery_profiles(tmp_path) -> None:
    from tangl.media.media_resource.resource_manager import ResourceManager
    from tangl.service.media import MediaContentProfile, MediaRenderProfile
    from tangl.service.world_registry import pop_manual_world, register_manual_world

    path = tmp_path / "logo.svg"
    path.write_text('<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12"/>')
    resources = ResourceManager(tmp_path)
    resources.index_directory(".")
    world = World.from_script_data(script_data={**_script(), "label": "public_logo_witness"},
                                   resources=resources)
    register_manual_world(world)
    try:
        manager = build_service_manager(PersistenceManagerFactory.native_in_mem())
        local = manager.get_world_media(world_id=world.label, media="logo.svg",
                                        render_profile=MediaRenderProfile(
                                            content_profile=MediaContentProfile.PASSTHROUGH))
        remote = manager.get_world_media(world_id=world.label, media="logo.svg")
        assert local["content_format"] == "path" and local["path"] == str(path)
        assert remote["content_format"] == "url"
        assert remote["url"] == f"/media/world/{world.label}/logo.svg"
        assert local["rit_id"] == remote["rit_id"] == str(resources.get_rit("logo.svg").uid)
        assert manager.get_world_media(world_id=world.label, media="absent.svg") is None
        path.write_text("version https://git-lfs.github.com/spec/v1\n")
        assert manager.get_world_media(world_id=world.label, media="logo.svg") is None
    finally:
        pop_manual_world(world.label)


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

        world.dispatch.register(
            advertise_rules,
            task="advertise_story_info_channels",
        )
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
