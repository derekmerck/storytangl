from __future__ import annotations
from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import pytest
import yaml

from tangl.core import Graph, StreamRegistry
from tangl.service import (
    AccessLevel,
    ApiEndpoint,
    AuthMode,
    HasApiEndpoints,
    MethodType,
    Orchestrator,
    ResponseType,
    ServiceConfig,
)
from tangl.service.controllers import RuntimeController, UserController
from tangl.service.response import InfoModel, RuntimeInfo
from tangl.service.user.user import User
from tangl.story.fabula.script_manager import ScriptManager
from tangl.story.fabula.world import World
from tangl.vm import ChoiceEdge, Frame, ResolutionPhase, Ledger


class FakePersistence(dict):
    def __init__(self) -> None:
        super().__init__()
        self.get_requests: list[UUID] = []
        self.saved: list[object] = []
        self.deleted: list[UUID] = []

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

    def remove(self, key) -> None:
        self.deleted.append(key)
        super().__delitem__(key)


class SimpleAck(RuntimeInfo):
    value: str


class SimpleController(HasApiEndpoints):
    @ApiEndpoint.annotate(response_type=ResponseType.RUNTIME)
    def get_value(self) -> RuntimeInfo:
        return RuntimeInfo.ok(message="ok", value="ok")


class CursorInfo(InfoModel):
    cursor_id: UUID


class LedgerController(HasApiEndpoints):
    def __init__(self) -> None:
        self.last_call: tuple[User, Ledger] | None = None

    @ApiEndpoint.annotate(response_type=ResponseType.INFO)
    def get_cursor(self, user: User, ledger: Ledger) -> CursorInfo:
        self.last_call = (user, ledger)
        return CursorInfo(cursor_id=ledger.cursor_id)


class FrameInfo(InfoModel):
    cursor_id: UUID


class FrameController(HasApiEndpoints):
    def __init__(self) -> None:
        self.frames: list[Frame] = []

    @ApiEndpoint.annotate(access_level=AccessLevel.PUBLIC, response_type=ResponseType.INFO)
    def get_frame_data(self, ledger: Ledger, frame: Frame) -> FrameInfo:
        self.frames.append(frame)
        return FrameInfo(cursor_id=frame.cursor_id)


class UpdateController(HasApiEndpoints):
    @ApiEndpoint.annotate(access_level=AccessLevel.USER, method_type=MethodType.UPDATE)
    def update_step(self, ledger: Ledger) -> RuntimeInfo:
        ledger.step += 1
        return RuntimeInfo.ok(step=ledger.step)


class ReadController(HasApiEndpoints):
    @ApiEndpoint.annotate(access_level=AccessLevel.USER, response_type=ResponseType.INFO)
    def get_cursor(self, ledger: Ledger) -> CursorInfo:
        return CursorInfo(cursor_id=ledger.cursor_id)


@pytest.fixture
def fake_persistence() -> FakePersistence:
    return FakePersistence()


@pytest.fixture
def orchestrator_with_acl(fake_persistence: FakePersistence) -> Orchestrator:
    config = ServiceConfig(
        auth_mode=AuthMode.ENFORCED,
        default_user_label="test",
        default_access_level=AccessLevel.USER,
    )
    return Orchestrator(fake_persistence, config=config)


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


def test_public_endpoint_runs_without_user(fake_persistence: FakePersistence) -> None:
    orchestrator = Orchestrator(fake_persistence)
    orchestrator.register_controller(UserController)

    result = orchestrator.execute("UserController.create_user", secret="dev-secret")

    assert isinstance(result, RuntimeInfo)
    assert result.status == "ok"
    assert result.details is not None
    assert "user_id" in result.details


def test_orchestrator_hydrates_user_and_ledger(
    fake_persistence: FakePersistence, minimal_ledger: Ledger
) -> None:
    ledger = minimal_ledger
    ledger_id = ledger.uid
    user = User(label="test_user", current_ledger_id=ledger_id, privileged=True)

    fake_persistence[user.uid] = user
    fake_persistence[ledger_id] = ledger.unstructure()

    orchestrator = Orchestrator(fake_persistence)
    orchestrator.register_controller(LedgerController)

    result = orchestrator.execute("LedgerController.get_cursor", user_id=user.uid)

    assert isinstance(result, CursorInfo)
    assert result.cursor_id == ledger.cursor_id
    controller_instance = orchestrator._endpoints["LedgerController.get_cursor"][0]
    assert controller_instance.last_call is not None
    hydrated_user, hydrated_ledger = controller_instance.last_call
    assert hydrated_user is user
    assert hydrated_ledger.uid == ledger_id

    ledger_gets = [key for key in fake_persistence.get_requests if key == ledger_id]
    assert len(ledger_gets) == 1


def test_orchestrator_requires_user_id_for_user_hydration(
    orchestrator_with_acl: Orchestrator, fake_persistence: FakePersistence, minimal_ledger: Ledger
) -> None:
    ledger_id = minimal_ledger.uid
    fake_persistence[ledger_id] = minimal_ledger.unstructure()

    orchestrator_with_acl.register_controller(LedgerController)

    result = orchestrator_with_acl.execute("LedgerController.get_cursor")

    assert isinstance(result, RuntimeInfo)
    assert result.status == "error"
    assert result.code == "ACCESS_DENIED"


def test_orchestrator_blocks_insufficient_access(
    orchestrator_with_acl: Orchestrator, fake_persistence: FakePersistence, minimal_ledger: Ledger
) -> None:
    ledger_id = minimal_ledger.uid
    user = User(label="player", current_ledger_id=ledger_id)
    fake_persistence[user.uid] = user
    fake_persistence[ledger_id] = minimal_ledger.unstructure()

    orchestrator_with_acl.register_controller(LedgerController)

    result = orchestrator_with_acl.execute("LedgerController.get_cursor", user_id=user.uid)

    assert isinstance(result, RuntimeInfo)
    assert result.status == "error"
    assert result.code == "ACCESS_DENIED"


def test_orchestrator_requires_active_story_for_inference(
    fake_persistence: FakePersistence,
) -> None:
    user = User(label="storyless")
    fake_persistence[user.uid] = user

    orchestrator = Orchestrator(fake_persistence)
    orchestrator.register_controller(ReadController)

    result = orchestrator.execute("ReadController.get_cursor", user_id=user.uid)

    assert isinstance(result, RuntimeInfo)
    assert result.status == "error"
    assert result.code == "NO_ACTIVE_STORY"


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
        assert isinstance(result, RuntimeInfo)
        return result.model_copy(update={"details": {**(result.details or {}), "post1": True}})

    def post_two(result):
        calls.append(("post", 2))
        assert isinstance(result, RuntimeInfo)
        return result.model_copy(update={"details": {**(result.details or {}), "post2": True}})

    class PipelineController(HasApiEndpoints):
        def __init__(self) -> None:
            self.last_frame: Frame | None = None

        @ApiEndpoint.annotate(
            access_level=AccessLevel.USER,
            preprocessors=[pre_one, pre_two],
            postprocessors=[post_one, post_two],
            method_type=MethodType.UPDATE,
            response_type=ResponseType.RUNTIME,
        )
        def resolve(self, ledger: Ledger, frame: Frame) -> RuntimeInfo:
            self.last_frame = frame
            edge = ledger.graph.find_edge(source=ledger.graph.get(ledger.cursor_id), destination=destination)
            frame.resolve_choice(edge or ChoiceEdge(
                graph=ledger.graph,
                source_id=ledger.cursor_id,
                destination_id=destination.uid,
            ))
            ledger.cursor_id = frame.cursor_id
            ledger.step = frame.step
            return RuntimeInfo.ok(
                cursor_id=ledger.cursor_id,
                step=ledger.step,
                cursor=str(ledger.cursor_id),
                step_value=ledger.step,
            )

    controller = PipelineController()
    orchestrator = Orchestrator(fake_persistence)
    orchestrator.register_controller(controller)

    fake_persistence[ledger.uid] = ledger.unstructure()
    user = User(label="pipeline-user", current_ledger_id=ledger.uid)
    fake_persistence[user.uid] = user

    result = orchestrator.execute(
        "PipelineController.resolve", user_id=user.uid, ledger_id=ledger.uid
    )

    assert calls == [("pre", 1), ("pre", 2), ("post", 1), ("post", 2)]
    assert isinstance(result, RuntimeInfo)
    assert result.cursor_id == destination.uid
    assert result.details is not None
    assert result.details.get("post1") is True and result.details.get("post2") is True
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
    user = User(label="mutator", current_ledger_id=ledger_id)
    fake_persistence[user.uid] = user

    orchestrator = Orchestrator(fake_persistence)
    orchestrator.register_controller(UpdateController)

    fake_persistence.saved.clear()
    orchestrator.execute(
        "UpdateController.update_step", user_id=user.uid, ledger_id=ledger_id
    )

    assert fake_persistence.saved
    saved_payload = fake_persistence.saved[-1]
    assert getattr(saved_payload, "uid", None) == ledger_id


def test_read_endpoint_does_not_write_back(
    fake_persistence: FakePersistence, minimal_ledger: Ledger
) -> None:
    ledger_id = minimal_ledger.uid
    fake_persistence[ledger_id] = minimal_ledger.unstructure()
    user = User(label="reader", current_ledger_id=ledger_id)
    fake_persistence[user.uid] = user

    orchestrator = Orchestrator(fake_persistence)
    orchestrator.register_controller(ReadController)

    fake_persistence.saved.clear()
    orchestrator.execute("ReadController.get_cursor", user_id=user.uid, ledger_id=ledger_id)
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

    assert isinstance(result, RuntimeInfo)
    assert result.details is not None

    ledger_id = UUID(result.details["ledger_id"])
    current_ledger_id = user.current_ledger_id
    assert current_ledger_id == ledger_id
    ledger_obj = result.details["ledger"]

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

def test_orchestrator_drop_story_deletes_ledger(
    fake_persistence: FakePersistence,
    minimal_ledger: Ledger,
) -> None:
    ledger = minimal_ledger
    ledger_id = ledger.uid
    user_id = uuid4()
    user = User(uid=user_id)
    user.current_ledger_id = ledger_id

    fake_persistence[user_id] = user
    fake_persistence[ledger_id] = ledger.unstructure()

    orchestrator = Orchestrator(fake_persistence)
    orchestrator.register_controller(RuntimeController)

    result = orchestrator.execute("RuntimeController.drop_story", user_id=user_id)

    assert isinstance(result, RuntimeInfo)
    assert result.status == "ok"
    assert result.details is not None
    assert result.details.get("archived") is False
    assert result.details.get("persistence_deleted") is True
    assert "_delete_ledger_id" not in result.details
    assert ledger_id in fake_persistence.deleted
    assert ledger_id not in fake_persistence
    persisted_user = fake_persistence[user_id]
    assert getattr(persisted_user, "current_ledger_id", None) is None
    assert any(isinstance(saved, User) and saved.uid == user_id for saved in fake_persistence.saved)
