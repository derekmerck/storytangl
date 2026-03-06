"""RuntimeController vm38/story38 endpoint flow tests."""

from __future__ import annotations

from tangl.core import Selector
from tangl.service.controllers.runtime_controller import RuntimeController
from tangl.service.user.user import User
from tangl.story import InitMode, World38
from tangl.story.episode import Action
from tangl.story.fragments import ChoiceFragment
from tangl.vm import Ledger


def _story38_script() -> dict:
    return {
        "label": "svc38_world",
        "metadata": {"title": "Svc 38", "author": "Tests", "start_at": "intro.start"},
        "scenes": {
            "intro": {
                "blocks": {
                    "start": {
                        "content": "Start",
                        "actions": [{"text": "Continue", "successor": "end"}],
                    },
                    "end": {"content": "End"},
                }
            }
        },
    }


def test_runtime_controller38_flow_create_info_update_resolve_drop() -> None:
    world = World38.from_script_data(script_data=_story38_script())
    controller = RuntimeController()
    user = User(label="runtime38-user")

    created = controller.create_story38(
        user=user,
        world_id=world.label,
        world=world,
        init_mode=InitMode.EAGER.value,
        story_label="svc38_story",
    )
    assert created.status == "ok"
    assert created.details is not None
    assert user.current_ledger_id is not None
    assert "envelope" in created.details
    ledger = created.details.get("ledger")
    assert isinstance(ledger, Ledger)

    created_envelope = created.details["envelope"]
    assert created_envelope["cursor_id"] == str(ledger.cursor_id)
    assert isinstance(created_envelope["fragments"], list)
    assert "last_redirect" in created_envelope
    assert "redirect_trace" in created_envelope

    info = controller.get_story_info38(ledger)
    assert info.status == "ok"
    assert info.details is not None
    assert info.details["choice_steps"] == ledger.choice_steps
    assert "last_redirect" in info.details
    assert "redirect_trace" in info.details

    update = controller.get_story_update38(ledger, since_step=0)
    assert update.status == "ok"
    assert update.details is not None
    update_envelope = update.details["envelope"]
    assert update_envelope["cursor_id"] == str(ledger.cursor_id)
    assert isinstance(update_envelope["fragments"], list)

    start = ledger.cursor
    choice = next(start.edges_out(Selector(has_kind=Action, trigger_phase=None)))
    resolved = controller.resolve_choice38(ledger, choice.uid)
    assert resolved.status == "ok"
    assert resolved.details is not None
    assert resolved.details["envelope"]["cursor_id"] == str(ledger.cursor_id)

    dropped = controller.drop_story38(user=user, ledger=ledger, archive=False)
    assert dropped.status == "ok"
    assert dropped.details is not None
    assert dropped.details["_delete_ledger_id"] == str(ledger.uid)
    assert user.current_ledger_id is None


def test_runtime_controller38_update_default_since_step_returns_full_history() -> None:
    world = World38.from_script_data(script_data=_story38_script())
    controller = RuntimeController()
    user = User(label="runtime38-user-default-update")

    created = controller.create_story38(
        user=user,
        world_id=world.label,
        world=world,
        init_mode=InitMode.EAGER.value,
        story_label="svc38_story_default_update",
    )
    ledger = created.details.get("ledger") if created.details else None
    assert isinstance(ledger, Ledger)

    start = ledger.cursor
    choice = next(start.edges_out(Selector(has_kind=Action, trigger_phase=None)))
    controller.resolve_choice38(ledger, choice.uid)

    update_default = controller.get_story_update38(ledger)
    update_full = controller.get_story_update38(ledger, since_step=0)

    assert update_default.status == "ok"
    assert update_full.status == "ok"
    assert update_default.details is not None
    assert update_full.details is not None
    assert update_default.details["envelope"]["fragments"] == update_full.details["envelope"]["fragments"]


def test_runtime_controller38_resolve_choice_accepts_choice_payload(monkeypatch) -> None:
    world = World38.from_script_data(script_data=_story38_script())
    controller = RuntimeController()
    user = User(label="runtime38-user-payload")

    created = controller.create_story38(
        user=user,
        world_id=world.label,
        world=world,
        init_mode=InitMode.EAGER.value,
        story_label="svc38_story_payload",
    )
    ledger = created.details.get("ledger") if created.details else None
    assert isinstance(ledger, Ledger)

    start = ledger.cursor
    choice = next(start.edges_out(Selector(has_kind=Action, trigger_phase=None)))

    captured: dict[str, object] = {}
    original_resolve = Ledger.resolve_choice

    def _capture(self, edge_id, *, choice_payload=None):
        captured["edge_id"] = edge_id
        captured["choice_payload"] = choice_payload
        return original_resolve(self, edge_id, choice_payload=choice_payload)

    monkeypatch.setattr(Ledger, "resolve_choice", _capture)

    payload = {"move": "knight", "to": "b6"}
    resolved = controller.resolve_choice38(ledger, choice.uid, choice_payload=payload)
    assert resolved.status == "ok"
    assert captured["edge_id"] == choice.uid
    assert captured["choice_payload"] == payload


def test_runtime_controller38_envelope_includes_blocker_diagnostics_metadata() -> None:
    world = World38.from_script_data(script_data=_story38_script())
    controller = RuntimeController()
    user = User(label="runtime38-user-blockers")

    created = controller.create_story38(
        user=user,
        world_id=world.label,
        world=world,
        init_mode=InitMode.EAGER.value,
        story_label="svc38_story_blockers",
    )
    ledger = created.details.get("ledger") if created.details else None
    assert isinstance(ledger, Ledger)

    blockers = [
        {
            "type": "dependency",
            "resolution_reason": "no_offers",
            "resolution_meta": {"alternatives": []},
        }
    ]
    envelope = controller._runtime38_envelope(
        ledger=ledger,
        fragments=[
            ChoiceFragment(
                edge_id=None,
                text="Locked",
                available=False,
                unavailable_reason="missing_dependency",
                blockers=blockers,
            )
        ],
    )
    assert envelope.metadata["blockers"][0]["unavailable_reason"] == "missing_dependency"
    assert envelope.metadata["blockers"][0]["blockers"] == blockers


def test_collect_blocker_diagnostics_accepts_legacy_kind_choice() -> None:
    blockers = [
        {
            "type": "dependency",
            "resolution_reason": "no_offers",
            "resolution_meta": {"alternatives": []},
        }
    ]
    fragments = [
        {
            "kind": "choice",
            "edge_id": "edge-1",
            "available": False,
            "unavailable_reason": "missing_dependency",
            "blockers": blockers,
        }
    ]
    diagnostics = RuntimeController._collect_blocker_diagnostics(fragments)
    assert diagnostics == [
        {
            "edge_id": "edge-1",
            "unavailable_reason": "missing_dependency",
            "blockers": blockers,
        }
    ]
