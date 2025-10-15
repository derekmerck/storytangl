from __future__ import annotations

import sys
import types

from pathlib import Path

from tangl.core.entity import Entity
from tangl.core.graph.graph import Graph
from tangl.media.media_resource.media_resource_inv_tag import MediaResourceInventoryTag as MediaRIT
from tangl.story.concepts.actor import Actor
from tangl.story.concepts.asset import AssetType
from tangl.story.fabula.world import World
from tangl.story.fabula.domain_manager import DomainManager
from tangl.story.fabula.script_manager import ScriptManager
from tangl.story.fabula.asset_manager import AssetManager
from tangl.media.resource_manager import ResourceManager


def test_domain_manager_resolve_builtin_class():
    manager = DomainManager()
    resolved = manager.resolve_class("tangl.story.concepts.actor.actor.Actor")
    assert resolved is Actor


def test_domain_manager_resolve_custom_class():
    class Elf(Actor):
        """Lightweight subclass for resolution testing."""

    manager = DomainManager()
    manager.register_class("Elf", Elf)
    assert manager.resolve_class("Elf") is Elf


def test_domain_manager_fallback_to_node():
    manager = DomainManager()
    from tangl.core.graph.node import Node

    assert manager.resolve_class("nonexistent.Class") is Node


def test_domain_manager_non_entity_class_falls_back_to_node():
    manager = DomainManager()
    from tangl.core.graph.node import Node

    resolved = manager.resolve_class("pathlib.Path")
    assert resolved is Node


def test_domain_manager_load_domain_module_registers_entities():
    manager = DomainManager()

    module = types.ModuleType("test_domain_module")

    class TempEntity(Entity):
        pass

    module.TempEntity = TempEntity
    sys.modules[module.__name__] = module
    try:
        manager.load_domain_module(module.__name__)
        assert manager.resolve_class("TempEntity") is TempEntity
    finally:
        sys.modules.pop(module.__name__, None)


def test_asset_manager_load_and_create_tokens():
    class TestAsset(AssetType):
        value: int = 0

    manager = AssetManager()
    manager.register_asset_class("test", TestAsset)

    try:
        manager.load_from_data("test", [{"label": "sword", "value": 50}])
        sword_type = manager.get_asset_type("test", "sword")
        assert sword_type.value == 50

        graph = Graph(label="asset_test")
        token = manager.create_token("test", "sword", graph)
        assert token.graph is graph
        assert token.reference_singleton is sword_type
    finally:
        TestAsset.clear_instances()


def test_resource_manager_index_and_lookup(tmp_path: Path):
    images_dir = tmp_path / "images"
    images_dir.mkdir()
    (images_dir / "test.png").write_bytes(b"fake image data")

    manager = ResourceManager(tmp_path)
    indexed = manager.index_directory("images")
    assert len(indexed) == 1

    try:
        rit = manager.get_rit("test.png")
        assert rit is not None
        assert rit.content_hash

        url = manager.get_url(rit)
        assert rit.content_hash.hex()[:16] in url
    finally:
        MediaRIT.clear_from_source_cache()


def test_world_initializes_managers():
    script_data = {
        "label": "test_script",
        "metadata": {"title": "Test Story", "author": "Author"},
    }
    script_manager = ScriptManager.from_data(script_data)

    world = World(label="test_world", script_manager=script_manager)

    try:
        assert world.script_manager is script_manager
        assert isinstance(world.domain_manager, DomainManager)
        assert isinstance(world.asset_manager, AssetManager)
        assert isinstance(world.resource_manager, ResourceManager)
        assert world.metadata["title"] == "Test Story"
        assert world.name == "Test Story"
        assert "countable" in world.asset_manager.asset_classes
    finally:
        World.clear_instances()
