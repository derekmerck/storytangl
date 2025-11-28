from __future__ import annotations

from pathlib import Path
from typing import Any, Union
from uuid import UUID, uuid4

import pytest
import yaml

from tangl.core import Graph, StreamRegistry
from tangl.service import ApiEndpoint, HasApiEndpoints, MethodType, Orchestrator, ResponseType
from tangl.service.controllers import RuntimeController
from tangl.service.response import InfoModel, RuntimeInfo
from tangl.service.user.user import User
from tangl.service.orchestrator import _CacheEntry
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


class StubUser:
    def __init__(self, uid: UUID, ledger_id: UUID) -> None:
        self.uid = uid
        self.current_ledger_id = ledger_id


class SimpleAck(RuntimeInfo):
    value: str


class SimpleController(HasApiEndpoints):
    @ApiEndpoint.annotate(response_type=ResponseType.RUNTIME, method_type=MethodType.READ)
    def get_value(self) -> RuntimeInfo:
        return RuntimeInfo.ok(message="ok", value="ok")


class CursorInfo(InfoModel):
    cursor_id: UUID


class LedgerController(HasApiEndpoints):
    def __init__(self) -> None:
        self.last_call: tuple[StubUser, Ledger] | None = None

    @ApiEndpoint.annotate(response_type=ResponseType.INFO, method_type=MethodType.READ)
    def get_cursor(self, user: StubUser, ledger: Ledger) -> CursorInfo:
        self.last_call = (user, ledger)
        return CursorInfo(cursor_id=ledger.cursor_id)


class FrameInfo(InfoModel):
    cursor_id: UUID


class FrameController(HasApiEndpoints):
    def __init__(self) -> None:
        self.frames: list[Frame] = []

    @ApiEndpoint.annotate(response_type=ResponseType.INFO, method_type=MethodType.READ)
    def get_frame_data(self, ledger: Ledger, frame: Frame) -> FrameInfo:
        self.frames.append(frame)
        return FrameInfo(cursor_id=frame.cursor_id)


class UpdateController(HasApiEndpoints):
    @ApiEndpoint.annotate(method_type=MethodType.UPDATE)
    def update_step(self, ledger: Ledger) -> RuntimeInfo:
        ledger.step += 1
        return RuntimeInfo.ok(step=ledger.step)


class ReadController(HasApiEndpoints):
    @ApiEndpoint.annotate(response_type=ResponseType.INFO, method_type=MethodType.READ)
    def get_cursor(self, ledger: Ledger) -> CursorInfo:
        return CursorInfo(cursor_id=ledger.cursor_id)


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

    result = orchestrator.execute("PipelineController.resolve", ledger_id=ledger.uid)

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


def test_orchestrator_build_ledger_passes_through_hydrated(
    fake_persistence: FakePersistence, minimal_ledger: Ledger
) -> None:
    hydrated = minimal_ledger
    fake_persistence[hydrated.uid] = hydrated

    orchestrator = Orchestrator(fake_persistence)

    class _LedgerEcho(HasApiEndpoints):
        @ApiEndpoint.annotate(response_type=ResponseType.INFO, method_type=MethodType.READ)
        def echo_cursor(self, ledger: Ledger) -> CursorInfo:
            return CursorInfo(cursor_id=ledger.cursor_id)

    orchestrator.register_controller(_LedgerEcho)

    result = orchestrator.execute("_LedgerEcho.echo_cursor", ledger_id=hydrated.uid)
    assert isinstance(result, CursorInfo)
    assert result.cursor_id == hydrated.cursor_id


def test_orchestrator_build_ledger_rejects_unsupported_payload(
    fake_persistence: FakePersistence,
) -> None:
    bogus_id = uuid4()
    fake_persistence[bogus_id] = object()

    orchestrator = Orchestrator(fake_persistence)

    class _LedgerUser(HasApiEndpoints):
        @ApiEndpoint.annotate(response_type=ResponseType.INFO, method_type=MethodType.READ)
        def needs_ledger(self, ledger: Ledger) -> CursorInfo:
            return CursorInfo(cursor_id=ledger.cursor_id)

    orchestrator.register_controller(_LedgerUser)

    with pytest.raises(TypeError, match="Unsupported ledger payload"):
        orchestrator.execute("_LedgerUser.needs_ledger", ledger_id=bogus_id)


def test_orchestrator_infer_ledger_id_requires_active_ledger(
    fake_persistence: FakePersistence,
) -> None:
    user_id = uuid4()
    user = StubUser(user_id, ledger_id=uuid4())
    user.current_ledger_id = None

    fake_persistence[user_id] = user

    orchestrator = Orchestrator(fake_persistence)

    class _NeedsLedger(HasApiEndpoints):
        @ApiEndpoint.annotate(response_type=ResponseType.INFO, method_type=MethodType.READ)
        def get_cursor(self, ledger: Ledger) -> CursorInfo:
            return CursorInfo(cursor_id=ledger.cursor_id)

    orchestrator.register_controller(_NeedsLedger)

    with pytest.raises(ValueError, match="User has no active ledger"):
        orchestrator.execute("_NeedsLedger.get_cursor", user_id=user_id)


def test_orchestrator_requires_persistence_for_ledger_hydration(minimal_ledger: Ledger) -> None:
    orchestrator = Orchestrator(persistence_manager=None)

    class _NeedsLedger(HasApiEndpoints):
        @ApiEndpoint.annotate(response_type=ResponseType.INFO, method_type=MethodType.READ)
        def needs_ledger(self, ledger: Ledger) -> CursorInfo:
            return CursorInfo(cursor_id=ledger.cursor_id)

    orchestrator.register_controller(_NeedsLedger)

    with pytest.raises(RuntimeError, match="Persistence manager required for resource hydration"):
        orchestrator.execute("_NeedsLedger.needs_ledger", ledger_id=minimal_ledger.uid)


def test_orchestrator_persists_with_plain_mapping(minimal_ledger: Ledger) -> None:
    store: dict[Any, Any] = {}
    store[minimal_ledger.uid] = minimal_ledger.unstructure()

    orchestrator = Orchestrator(store)
    orchestrator.register_controller(UpdateController)

    orchestrator.execute("UpdateController.update_step", ledger_id=minimal_ledger.uid)

    saved = store[minimal_ledger.uid]
    assert isinstance(saved, Ledger)
    assert getattr(saved, "uid", None) == minimal_ledger.uid


def test_orchestrator_persists_mapping_payload() -> None:
    store: dict[Any, Any] = {}

    class _SavesMapping(HasApiEndpoints):
        @ApiEndpoint.annotate(method_type=MethodType.UPDATE)
        def save_mapping(self) -> RuntimeInfo:
            return RuntimeInfo.ok(ledger={"ledger_uid": uuid4()})

    orch = Orchestrator(store)
    orch.register_controller(_SavesMapping)

    payload = {"ledger_uid": uuid4()}
    orch._resource_cache["dummy"] = _CacheEntry(resource=payload, dirty=True)

    orch._write_back_resources()
    assert any(isinstance(key, UUID) or isinstance(value, dict) for key, value in store.items())


class OptionalUserController(HasApiEndpoints):
    def __init__(self) -> None:
        self.seen_user: StubUser | None = None

    @ApiEndpoint.annotate(response_type=ResponseType.INFO, method_type=MethodType.READ)
    def who(self, user: Union[StubUser, None]) -> InfoModel:
        self.seen_user = user
        return InfoModel(message="ok")


def test_orchestrator_resolves_union_user_type(fake_persistence: FakePersistence) -> None:
    user_id = uuid4()
    ledger_id = uuid4()
    user = StubUser(user_id, ledger_id)
    fake_persistence[user_id] = user
    fake_persistence[ledger_id] = {
        "ledger_uid": ledger_id,
        "graph": None,
        "cursor_id": None,
        "records": {},
    }

    controller = OptionalUserController()
    orchestrator = Orchestrator(fake_persistence)
    orchestrator.register_controller(controller)

    orchestrator.execute("OptionalUserController.who", user_id=user_id)
    assert controller.seen_user is user
