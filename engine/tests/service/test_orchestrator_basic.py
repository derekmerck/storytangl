from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import pytest
import yaml

from tangl.core import Graph, StreamRegistry
from tangl.service import ApiEndpoint, HasApiEndpoints, MethodType, Orchestrator, ResponseType
from tangl.service.controllers import RuntimeController
from tangl.service.user.user import User
from tangl.story.fabula.script_manager import ScriptManager
from tangl.story.fabula.world import World
from tangl.vm import ChoiceEdge, Frame, ResolutionPhase, Ledger


class FakePersistence(dict):
    def __init__(self) -> None:
        super().__init__()
        self.get_requests: list[UUID] = []
        self.saved: list[object] = []

    def get(self, key, default=None):
        self.get_requests.append(key)
        return super().get(key, default)

    def save(self, value) -> None:
        self.saved.append(value)
        key = getattr(value, "uid", None)
        if key is None and isinstance(value, dict):
            key = value.get("uid") or value.get("ledger_uid")
        if key is None:
            raise ValueError("Unable to determine key for saved value")
        super().__setitem__(key, value)


class StubUser:
    def __init__(self, uid: UUID, ledger_id: UUID) -> None:
        self.uid = uid
        self.current_ledger_id = ledger_id


class SimpleController(HasApiEndpoints):
    @ApiEndpoint.annotate(response_type=ResponseType.INFO)
    def get_value(self) -> str:
        return "ok"


class LedgerController(HasApiEndpoints):
    def __init__(self) -> None:
        self.last_call: tuple[StubUser, Ledger] | None = None

    @ApiEndpoint.annotate(response_type=ResponseType.INFO)
    def get_cursor(self, user: StubUser, ledger: Ledger) -> UUID:
        self.last_call = (user, ledger)
        return ledger.cursor_id


class FrameController(HasApiEndpoints):
    def __init__(self) -> None:
        self.frames: list[Frame] = []

    @ApiEndpoint.annotate(response_type=ResponseType.CONTENT)
    def get_frame_data(self, ledger: Ledger, frame: Frame) -> Frame:
        self.frames.append(frame)
        return frame


class UpdateController(HasApiEndpoints):
    @ApiEndpoint.annotate(method_type=MethodType.UPDATE)
    def update_step(self, ledger: Ledger) -> int:
        ledger.step += 1
        return ledger.step


class ReadController(HasApiEndpoints):
    @ApiEndpoint.annotate(response_type=ResponseType.INFO)
    def get_cursor(self, ledger: Ledger) -> UUID:
        return ledger.cursor_id


@pytest.fixture
def fake_persistence() -> FakePersistence:
    return FakePersistence()


@pytest.fixture
def minimal_ledger() -> Ledger:
    graph = Graph()
    start = graph.add_node(label="start")
    ledger = Ledger(graph=graph, cursor_id=start.uid, records=StreamRegistry())
    ledger.push_snapshot()
    return ledger


def test_orchestrator_registers_endpoints(fake_persistence: FakePersistence) -> None:
    orchestrator = Orchestrator(fake_persistence)
    orchestrator.register_controller(SimpleController)
    assert "SimpleController.get_value" in orchestrator._endpoints


def test_orchestrator_hydrates_user_and_ledger(
    fake_persistence: FakePersistence, minimal_ledger: Ledger
) -> None:
    ledger = minimal_ledger
    ledger_id = ledger.uid
    user_id = uuid4()
    user = StubUser(user_id, ledger_id)

    fake_persistence[user_id] = user
    fake_persistence[ledger_id] = ledger.unstructure()

    orchestrator = Orchestrator(fake_persistence)
    orchestrator.register_controller(LedgerController)

    result = orchestrator.execute("LedgerController.get_cursor", user_id=user_id)

    assert result == ledger.cursor_id
    controller_instance = orchestrator._endpoints["LedgerController.get_cursor"][0]
    assert controller_instance.last_call is not None
    hydrated_user, hydrated_ledger = controller_instance.last_call
    assert hydrated_user is user
    assert hydrated_ledger.uid == ledger_id

    ledger_gets = [key for key in fake_persistence.get_requests if key == ledger_id]
    assert len(ledger_gets) == 1


def test_orchestrator_requires_user_id_for_user_hydration(
    fake_persistence: FakePersistence, minimal_ledger: Ledger
) -> None:
    ledger_id = minimal_ledger.uid
    fake_persistence[ledger_id] = minimal_ledger.unstructure()

    orchestrator = Orchestrator(fake_persistence)
    orchestrator.register_controller(LedgerController)

    with pytest.raises(ValueError, match="user_id is required"):
        orchestrator.execute("LedgerController.get_cursor")


def test_orchestrator_reuses_cached_ledger_for_frame(
    fake_persistence: FakePersistence, minimal_ledger: Ledger
) -> None:
    ledger_id = minimal_ledger.uid
    fake_persistence[ledger_id] = minimal_ledger.unstructure()

    orchestrator = Orchestrator(fake_persistence)
    orchestrator.register_controller(FrameController)

    fake_persistence.get_requests.clear()
    orchestrator.execute("FrameController.get_frame_data", ledger_id=ledger_id)

    ledger_gets = [key for key in fake_persistence.get_requests if key == ledger_id]
    assert len(ledger_gets) == 1
    controller_instance = orchestrator._endpoints["FrameController.get_frame_data"][0]
    assert controller_instance.frames


def test_orchestrator_pipeline_smoke(
    fake_persistence: FakePersistence, minimal_ledger: Ledger
) -> None:
    ledger = minimal_ledger
    start_node = ledger.graph.get(ledger.cursor_id)
    destination = ledger.graph.add_node(label="dest")
    ChoiceEdge(
        graph=ledger.graph,
        source_id=start_node.uid if start_node else None,
        destination_id=destination.uid,
    )

    calls: list[tuple[str, int]] = []

    def pre_one(args, kwargs):
        calls.append(("pre", 1))
        return args, kwargs

    def pre_two(args, kwargs):
        calls.append(("pre", 2))
        return args, kwargs

    def post_one(result):
        calls.append(("post", 1))
        payload = dict(result)
        payload["post1"] = True
        return payload

    def post_two(result):
        calls.append(("post", 2))
        payload = dict(result)
        payload["post2"] = True
        return payload

    class PipelineController(HasApiEndpoints):
        def __init__(self) -> None:
            self.last_frame: Frame | None = None

        @ApiEndpoint.annotate(
            preprocessors=[pre_one, pre_two],
            postprocessors=[post_one, post_two],
            method_type=MethodType.UPDATE,
            response_type=ResponseType.RUNTIME,
        )
        def resolve(self, ledger: Ledger, frame: Frame) -> dict[str, Any]:
            self.last_frame = frame
            edge = ledger.graph.find_edge(source=ledger.graph.get(ledger.cursor_id), destination=destination)
            frame.resolve_choice(edge or ChoiceEdge(
                graph=ledger.graph,
                source_id=ledger.cursor_id,
                destination_id=destination.uid,
            ))
            ledger.cursor_id = frame.cursor_id
            ledger.step = frame.step
            return {"cursor": str(ledger.cursor_id), "step": ledger.step}

    controller = PipelineController()
    orchestrator = Orchestrator(fake_persistence)
    orchestrator.register_controller(controller)

    fake_persistence[ledger.uid] = ledger.unstructure()

    result = orchestrator.execute("PipelineController.resolve", ledger_id=ledger.uid)

    assert calls == [("pre", 1), ("pre", 2), ("post", 1), ("post", 2)]
    assert result["cursor"] == str(destination.uid)
    assert result["post1"] is True and result["post2"] is True
    persisted_ledger = fake_persistence[ledger.uid]
    assert getattr(persisted_ledger, "cursor_id") == destination.uid
    assert getattr(persisted_ledger, "step") > 0

    assert "frame" in persisted_ledger.records.markers
    assert any(
        name.startswith("step-") for name in persisted_ledger.records.markers["frame"]
    )

    assert controller.last_frame is not None
    assert ResolutionPhase.VALIDATE in controller.last_frame.phase_receipts


def test_orchestrator_persists_mutations(
    fake_persistence: FakePersistence, minimal_ledger: Ledger
) -> None:
    ledger_id = minimal_ledger.uid
    fake_persistence[ledger_id] = minimal_ledger.unstructure()

    orchestrator = Orchestrator(fake_persistence)
    orchestrator.register_controller(UpdateController)

    fake_persistence.saved.clear()
    orchestrator.execute("UpdateController.update_step", ledger_id=ledger_id)

    assert fake_persistence.saved
    saved_payload = fake_persistence.saved[-1]
    assert getattr(saved_payload, "uid", None) == ledger_id


def test_read_endpoint_does_not_write_back(
    fake_persistence: FakePersistence, minimal_ledger: Ledger
) -> None:
    ledger_id = minimal_ledger.uid
    fake_persistence[ledger_id] = minimal_ledger.unstructure()

    orchestrator = Orchestrator(fake_persistence)
    orchestrator.register_controller(ReadController)

    fake_persistence.saved.clear()
    orchestrator.execute("ReadController.get_cursor", ledger_id=ledger_id)
    assert not fake_persistence.saved


def test_create_story_via_orchestrator_persists_ledger(
    fake_persistence: FakePersistence,
) -> None:
    World.clear_instances()
    script_path = Path(__file__).resolve().parents[1] / "resources" / "demo_script.yaml"
    data = yaml.safe_load(script_path.read_text())
    script_manager = ScriptManager.from_data(data)
    world = World(label="demo_world", script_manager=script_manager)

    user = User(label="player")
    fake_persistence.save(user)
    fake_persistence.saved.clear()

    orchestrator = Orchestrator(fake_persistence)
    orchestrator.register_controller(RuntimeController)

    result = orchestrator.execute(
        "RuntimeController.create_story",
        user_id=user.uid,
        world_id=world.label,
    )

    ledger_id = UUID(result["ledger_id"])
    current_ledger_id = user.current_ledger_id
    assert current_ledger_id == ledger_id
    ledger_obj = result["ledger"]

    fake_persistence.save(ledger_obj)

    assert ledger_id in fake_persistence
    saved_payload = fake_persistence[ledger_id]
    stored_id = getattr(saved_payload, "uid", getattr(saved_payload, "ledger_uid", None))
    assert stored_id == ledger_id
    assert any(getattr(item, "uid", None) == user.uid for item in fake_persistence.saved)
    assert any(
        getattr(item, "uid", getattr(item, "ledger_uid", None)) == ledger_id
        for item in fake_persistence.saved
    )

    World.clear_instances()
