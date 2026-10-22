"""A tiny JSON-backed text choice, shared by Service and real CLI witnesses."""

from __future__ import annotations

from tangl.core import BehaviorRegistry
from tangl.persistence import PersistenceManagerFactory
from tangl.presentation.intent import Accepts
from tangl.service import ServiceManager
from tangl.service.response import RuntimeEnvelope
from tangl.service.user import User
from tangl.story import World
from tangl.vm.runtime.frame import PhaseCtx


def text_choice_session(
    accepts: Accepts | None, *, payload: object = None, available: bool = True,
    activation: str | None = None,
) -> tuple[World, ServiceManager, User, RuntimeEnvelope]:
    world = World.from_script_data(script_data={
        "label": "text_submission",
        "metadata": {"start_at": "intro.start"},
        "globals": {"answer": "untouched", "effect_count": 0, "activation": {}},
        "scenes": {"intro": {"blocks": {
            "start": {"content": "Your answer?", "actions": [{
                "text": "Answer", "successor": "end",
                # Author-facing schema input, not the persistence path under test.
                "accepts": accepts.model_dump(mode="python") if accepts is not None else None,
                "payload": payload, "conditions": [] if available else ["False"],
                "activation": activation,
                "effects": [
                    "graph.locals['answer'] = submitted['text']",
                    "graph.locals['activation'] = submitted.copy()",
                    "graph.locals['effect_count'] += 1",
                ],
            }]},
            "end": {"content": "Answer saved."},
        }}},
    })
    authority = BehaviorRegistry(label="text_fixture_namespace")

    def submitted_value(*, ctx: PhaseCtx, **_kw: object) -> dict[str, object]:
        # Ordinary world namespace policy lets an authored effect read the
        # effective payload; the generic engine need not publish input fields.
        return {"submitted": ctx.selected_payload}

    authority.register(submitted_value, task="gather_ns")
    world.extra_authorities.append(authority)
    persistence = PersistenceManagerFactory.create_persistence_manager(
        manager_name="json_sqlite_in_mem",
    )
    manager = ServiceManager(persistence)
    user = User(label="text_reader")
    persistence.save(user)
    envelope = manager.create_story(user_id=user.uid, world_id=world.label, world=world)
    return world, manager, user, envelope
