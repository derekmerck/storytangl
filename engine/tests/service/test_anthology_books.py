"""Each book of an anthology is a world a client can open by id (#610).

Before this, only code that compiled an anthology itself and passed the
``World`` in could play one: ``create_story(world_id=<anthology>)`` compiled the
whole bundle as one world with the default codec, and no id named a book.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tangl.journal.fragments import ContentFragment
from tangl.persistence import PersistenceManagerFactory
from tangl.service import ServiceManager
from tangl.service import world_registry
from tangl.service.user.user import User
from tangl.service.world_registry import WorldRegistry
from tangl.story import World

SEARCH_ROOT = Path(__file__).resolve().parents[1] / "resources" / "anthology_worlds"


@pytest.fixture
def registry() -> WorldRegistry:
    # Worlds are singletons by label, so each test compiles its books afresh.
    World.clear_instances()
    yield WorldRegistry(world_dirs=[SEARCH_ROOT])
    World.clear_instances()


def test_each_book_is_listed_as_a_world_of_its_anthology(registry: WorldRegistry) -> None:
    worlds = {world["label"]: world for world in registry.list_worlds()}

    assert set(worlds) == {"shelf_first", "shelf_second", "pamphlet"}
    assert worlds["shelf_first"]["anthology"] == "shelf"
    assert worlds["pamphlet"]["anthology"] is None
    # A book's own title wins; one that declares none is named after its anthology.
    assert worlds["shelf_first"]["metadata"]["title"] == "The First Book"
    assert worlds["shelf_second"]["metadata"]["title"] == "The Shelf: second"
    # Everything else comes from the anthology.
    assert worlds["shelf_second"]["metadata"]["author"] == "Tests"


def test_a_book_opens_by_its_own_id(registry: WorldRegistry) -> None:
    world = registry.get_world("shelf_second")

    assert world.label == "shelf_second"
    assert registry.get_world("shelf_second") is world


def test_the_anthology_itself_is_not_a_world(registry: WorldRegistry) -> None:
    with pytest.raises(
        ValueError, match="shelf is an anthology; open one of its books: shelf_first, shelf_second"
    ):
        registry.get_world("shelf")


@pytest.fixture
def manager(monkeypatch: pytest.MonkeyPatch) -> ServiceManager:
    monkeypatch.setattr(world_registry, "get_world_dirs", lambda: [SEARCH_ROOT])
    monkeypatch.setattr(world_registry, "_MANUAL_WORLDS", {})
    monkeypatch.setattr(world_registry, "_DISCOVERED_REGISTRIES", {})
    World.clear_instances()
    yield ServiceManager(PersistenceManagerFactory.native_in_mem())
    World.clear_instances()


def test_the_service_lists_books_with_their_anthology(manager: ServiceManager) -> None:
    books = {world.label: world.anthology for world in manager.list_worlds()}

    assert books == {"shelf_first": "shelf", "shelf_second": "shelf", "pamphlet": None}


def test_the_service_creates_a_story_in_a_book_by_id(manager: ServiceManager) -> None:
    user = User(label="anthology-reader")
    manager.persistence.save(user)

    envelope = manager.create_story(user_id=user.uid, world_id="shelf_second")

    text = " ".join(
        fragment.content for fragment in envelope.fragments if isinstance(fragment, ContentFragment)
    )
    assert "The second book opens." in text
