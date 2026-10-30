"""Service prepares the exact World before ordinary constructor-form restoration."""

from __future__ import annotations

from pathlib import Path
import shutil
from uuid import UUID

import pytest

from tangl.core import Graph, GraphFactory, Registry
from tangl.loaders import WorldBundle, WorldCompiler
from tangl.persistence import PersistenceManager, PersistenceManagerFactory
from tangl.service import ServiceManager
from tangl.service import world_registry
from tangl.story import World
from tangl.vm import Ledger


class SuppliedWorld(World):
    """Witness that the exact already-registered authority kind is preserved."""


SavedStory = tuple[ServiceManager, PersistenceManager, UUID, UUID, Path]


@pytest.fixture
def saved_story(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> SavedStory:
    monkeypatch.setattr(World, "_instances", Registry())
    monkeypatch.setattr(world_registry, "_MANUAL_WORLDS", {})
    monkeypatch.setattr(world_registry, "_DISCOVERED_REGISTRIES", {})
    monkeypatch.setattr(world_registry, "get_world_dirs", lambda: [tmp_path])
    repo = Path(__file__).resolve().parents[3]
    shutil.copytree(repo / "worlds/reference", tmp_path / "reference")
    unrelated = tmp_path / "unrelated"
    unrelated.mkdir()
    (unrelated / "world.yaml").write_text("label: unrelated\n", encoding="utf-8")
    (unrelated / "script.yaml").write_text("scenes: {}\n", encoding="utf-8")
    persistence = PersistenceManagerFactory.json_file(base_path=tmp_path / "store")
    service = ServiceManager(persistence)
    user_id = UUID(service.create_user(secret="world-restore").details["user_id"])
    envelope = service.create_story(user_id=user_id, world_id="reference")
    ledger_id = UUID(envelope.metadata["ledger_id"])
    return service, persistence, user_id, ledger_id, tmp_path


@pytest.mark.parametrize("entry", ["load", "open", "session"])
def test_service_prepares_only_the_referenced_world(
    saved_story: SavedStory, monkeypatch: pytest.MonkeyPatch, entry: str,
) -> None:
    service, persistence, user_id, ledger_id, _root = saved_story
    before = persistence.read_record(ledger_id)
    World.clear_instances()
    world_registry.clear_discovered_world_registries()
    compiled = []
    compile_world = WorldCompiler.compile

    def record_compile(
        self: WorldCompiler, bundle: WorldBundle, story_key: str | None = None
    ) -> World:
        compiled.append(bundle.manifest.label)
        return compile_world(self, bundle, story_key=story_key)

    monkeypatch.setattr(WorldCompiler, "compile", record_compile)
    if entry == "load":
        restored = service._load_ledger(ledger_id)
    elif entry == "open":
        with service.open_ledger(ledger_id) as restored:
            assert restored.uid == ledger_id
    else:
        with service.open_session(user_id=user_id) as session:
            restored = session.ledger
    assert compiled == ["reference"]
    assert restored.graph.factory is World.get_instance("reference")
    assert restored.cursor_id == before["cursor_id"]
    assert persistence.read_record(ledger_id)["graph"]["factory"] == before["graph"]["factory"]


def test_registered_manual_world_is_reused_without_a_bundle(
    saved_story: SavedStory, monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, _persistence, _user_id, ledger_id, root = saved_story
    registered = World.get_instance("reference")
    shutil.rmtree(root / "reference")
    monkeypatch.setattr(service, "open_world", lambda _: pytest.fail("Recompiled live authority"))
    with service.open_ledger(ledger_id) as ledger:
        assert ledger.graph.factory is registered


@pytest.mark.parametrize("missing", [True, False])
def test_missing_world_does_not_mutate_saved_ledger_or_user_pointer(
    saved_story: SavedStory, missing: bool,
) -> None:
    service, persistence, user_id, ledger_id, root = saved_story
    before_ledger = persistence.storage[ledger_id]
    before_user = persistence.storage[user_id]
    World.clear_instances()
    world_registry.clear_discovered_world_registries()
    if missing:
        shutil.rmtree(root / "reference")
    else:
        (root / "reference/script.yaml").unlink()
    with pytest.raises(ValueError, match="Unknown world: reference|No scripts found"):
        with service.open_session(user_id=user_id, write_back=True):
            pytest.fail("Missing World opened")
    assert persistence.storage[ledger_id] == before_ledger
    assert persistence.storage[user_id] == before_user
    assert service.get_user_info(user_id=user_id).current_ledger_id == ledger_id
    assert World.get_instance("reference") is None


@pytest.mark.parametrize("profile", ["native_in_mem", "json_file"])
@pytest.mark.parametrize("core_factory", [False, True])
def test_non_world_graphs_do_not_trigger_world_resolution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, profile: str, core_factory: bool,
) -> None:
    monkeypatch.setattr(GraphFactory, "_instances", Registry())
    factory = GraphFactory(label="reference") if core_factory else None
    graph = Graph(factory=factory)
    node = graph.add_node(label="start")
    ledger = Ledger.from_graph(graph=graph, entry_id=node.uid)
    persistence = PersistenceManagerFactory.create_persistence_manager(
        manager_name=profile, user_data_path=tmp_path,
    )
    service = ServiceManager(persistence)
    persistence.save(ledger)
    monkeypatch.setattr(
        service, "open_world", lambda _: pytest.fail("Resolved a non-World factory"),
    )
    with service.open_ledger(ledger.uid) as restored:
        assert restored.graph.factory is factory
        if profile == "native_in_mem":
            assert restored is ledger


def test_manually_supplied_world_kind_is_reused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(SuppliedWorld, "_instances", Registry())
    world = SuppliedWorld.from_script_data(script_data={
        "label": "manually_supplied", "metadata": {"start_at": "intro.start"},
        "scenes": {"intro": {"blocks": {"start": {"content": "Start"}}}},
    })
    persistence = PersistenceManagerFactory.json_file(base_path=tmp_path)
    service = ServiceManager(persistence)
    user_id = UUID(service.create_user(secret="manual-world").details["user_id"])
    envelope = service.create_story(user_id=user_id, world_id=world.label, world=world)
    ledger_id = UUID(envelope.metadata["ledger_id"])
    monkeypatch.setattr(service, "open_world", lambda _: pytest.fail("Recompiled manual World"))
    with service.open_ledger(ledger_id) as restored:
        assert restored.graph.factory is world


def test_unavailable_core_factory_still_rejects_without_world_fallback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(GraphFactory, "_instances", Registry())
    factory = GraphFactory(label="reference")
    graph = Graph(factory=factory)
    node = graph.add_node(label="start")
    ledger = Ledger.from_graph(graph=graph, entry_id=node.uid)
    persistence = PersistenceManagerFactory.json_file(base_path=tmp_path)
    service = ServiceManager(persistence)
    persistence.save(ledger)
    GraphFactory.clear_instances()
    monkeypatch.setattr(
        service, "open_world", lambda _: pytest.fail("Core factory resolved as World"),
    )
    with pytest.raises(LookupError, match="Persisted graph factory reference"):
        with service.open_ledger(ledger.uid):
            pytest.fail("Missing Core factory opened")
