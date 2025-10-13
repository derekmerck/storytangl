from __future__ import annotations

from pathlib import Path
from uuid import UUID, uuid4

import pytest
import yaml

from tangl.core import Graph, StreamRegistry
from tangl.service import ApiEndpoint, HasApiEndpoints, MethodType, Orchestrator, ResponseType
from tangl.service.controllers import RuntimeController
from tangl.service.user.user import User
from tangl.compiler.script_manager import ScriptManager
from tangl.story.story_domain.world import World
from tangl.vm.frame import Frame
from tangl.vm.ledger import Ledger


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
    current_ledger_id = getattr(user, "current_ledger_id", None)
    if current_ledger_id is not None:
        assert current_ledger_id == ledger_id
    assert user.current_story_id == ledger_id
    ledger_obj = result["ledger"]
    fake_persistence.save(LedgerEnvelope.from_ledger(ledger_obj))

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
