from __future__ import annotations

from typing import Any

from tangl.core import Selector
from tangl.persistence import PersistenceManagerFactory
from tangl.service.service_manager import ServiceManager
from tangl.service.user.user import User
from tangl.story import InitMode, World
from tangl.story.episode import Action
from tangl.vm.runtime.ledger import Ledger


def _story_script() -> dict[str, Any]:
    return {
        "label": "integration_world",
        "metadata": {
            "title": "Integration Story",
            "author": "tests",
            "start_at": "intro.start",
        },
        "scenes": {
            "intro": {
                "blocks": {
                    "start": {
                        "content": "Start",
                        "actions": [{"text": "Continue", "successor": "end"}],
                    },
                    "end": {
                        "content": "End",
                        "media": [{"name": "end.svg", "media_role": "narrative_im"}],
                    },
                },
            },
        },
    }


def _first_choice_edge(ledger: Ledger) -> Action:
    return next(ledger.cursor.edges_out(Selector(has_kind=Action, trigger_phase=None)))


def _create_story_session() -> tuple[ServiceManager, User, Ledger]:
    persistence = PersistenceManagerFactory.native_in_mem()
    user = User(label="integration-user")
    persistence.save(user)

    manager = ServiceManager(persistence)
    world = World.from_script_data(script_data=_story_script())
    created = manager.create_story(
        user_id=user.uid,
        world_id=world.label,
        world=world,
        init_mode=InitMode.EAGER.value,
        story_label="integration_story",
    )

    assert created.metadata.get("world_id") == world.label
    assert user.current_ledger_id is not None
    persisted_ledger = persistence.load(user.current_ledger_id)
    assert isinstance(persisted_ledger, Ledger)
    return manager, user, persisted_ledger


def test_story_choice_resolution_flow() -> None:
    manager, user, ledger = _create_story_session()

    old_cursor = ledger.cursor_id
    old_step = ledger.step
    choice = _first_choice_edge(ledger)

    resolved = manager.resolve_choice(
        user_id=user.uid,
        choice_id=choice.uid,
    )

    assert resolved.cursor_id != old_cursor
    updated_ledger = manager.persistence.load(ledger.uid)
    assert isinstance(updated_ledger, Ledger)
    assert updated_ledger.step > old_step
    assert updated_ledger.cursor_id != old_cursor

    update = manager.get_story_update(
        user_id=user.uid,
        since_step=-1,
    )
    media_fragments = [
        fragment
        for fragment in update.fragments
        if getattr(fragment, "fragment_type", None) == "media"
    ]
    assert media_fragments


def test_story_read_endpoint_does_not_persist() -> None:
    manager, user, ledger = _create_story_session()
    baseline = manager.persistence.load(ledger.uid)
    assert isinstance(baseline, Ledger)

    info = manager.get_story_update(
        user_id=user.uid,
        since_step=0,
    )

    assert info.cursor_id == baseline.cursor_id
    after = manager.persistence.load(ledger.uid)
    assert isinstance(after, Ledger)
    assert after.step == baseline.step
    assert after.cursor_id == baseline.cursor_id
