"""Shared fixtures and helper classes for core38 trait tests."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from pydantic import Field

from tangl.core.bases import (
    HasContent,
    HasIdentity,
    HasOrder,
    HasState,
    Unstructurable,
    is_identifier,
)
from tangl.core.singleton import Singleton
from tangl.core.token import Token
from tangl.core.record import Record
from tangl.core.entity import Entity


class SimpleEntity(Unstructurable, HasIdentity):
    """Minimal composable entity for tests."""


class Person(Unstructurable, HasIdentity):
    """Entity with extra fields."""

    name: str | None = None
    age: int | None = None


class Character(Unstructurable, HasIdentity):
    """Entity with custom field and method identifiers."""

    name: str = Field(..., json_schema_extra={"is_identifier": True})

    @is_identifier
    def nickname(self) -> str:
        return f"nick_{self.name.lower()}"


class ContentEntity(HasContent, HasIdentity):
    """Entity with content-based equality."""

    content: str

    def get_hashable_content(self) -> str:
        return self.content


class OrderedEntity(HasOrder, HasIdentity):
    """Entity with ordering and identity traits."""


class FullEntity(HasState, HasContent, HasOrder, Unstructurable, HasIdentity):
    """Entity composing all major core38 traits."""

    content: str = "default"

    def get_hashable_content(self) -> str:
        return self.content


class WeaponType(Singleton):
    """Test singleton for token wrapping."""

    damage: str
    sharpness: float = Field(1.0, json_schema_extra={"instance_var": True})

    def __repr__(self) -> str:
        return (
            f"<{self.__class__.__name__}:{self.get_label()}"
            f"(damage={self.damage}, sharpness={self.sharpness})>"
        )

    def describe(self) -> str:
        return f"A {self.get_label()} dealing {self.damage} damage"


class ArmorType(Singleton):
    """Second singleton type for cross-type token tests."""

    defense: int
    condition: float = Field(1.0, json_schema_extra={"instance_var": True})


class NPCType(Singleton):
    """Singleton for method rebinding tests."""

    hp: int = 100
    name: str = Field("unnamed", json_schema_extra={"instance_var": True})

    def greet(self) -> str:
        return f"I am {self.name}"


class SimpleRecord(Record):
    """Record subclass with canonical content field."""

    content: str = ""


class PayloadRecord(Record):
    """Record subclass exposing payload-backed content."""

    payload: dict = Field(default_factory=dict)


class CustomRecord(Record):
    """Record subclass used for extra-field allowance checks."""


class PriorityRecord(Record):
    """Record with a composite ordering key."""

    content: str = ""
    priority: int = 0

    def sort_key(self):
        return self.priority, self.seq


class Scene(Entity):
    """Test entity kind for template payload behavior."""

    location: str = "unknown"


class Block(Entity):
    """Secondary test entity kind."""

    content: str = ""


class SpecialScene(Scene):
    """Subtype used for template materialize kind narrowing tests."""

    difficulty: int = 1


@pytest.fixture
def null_ctx() -> SimpleNamespace:
    """Minimal context satisfying dispatch's registry/inline behavior contract."""
    return SimpleNamespace(
        get_registries=lambda: [],
        get_inline_behaviors=lambda: [],
    )


@pytest.fixture
def mock_ctx_with_registry() -> tuple[SimpleNamespace, object]:
    """Context paired with a fresh behavior registry for hook tests."""
    from tangl.core.behavior import BehaviorRegistry

    registry = BehaviorRegistry()
    ctx = SimpleNamespace(
        get_registries=lambda: [registry],
        get_inline_behaviors=lambda: [],
    )
    return ctx, registry


@pytest.fixture
def inline_ctx() -> callable:
    """Build a context object carrying inline behaviors only."""

    def _make(*funcs):
        return SimpleNamespace(
            get_registries=lambda: [],
            get_inline_behaviors=lambda: list(funcs),
        )

    return _make


@pytest.fixture
def layered_ctx() -> callable:
    """Build a context containing registries at named dispatch layers."""
    from tangl.core.behavior import BehaviorRegistry, DispatchLayer

    def _make(**layer_funcs):
        registries = []
        for layer_name, funcs in layer_funcs.items():
            layer = DispatchLayer[layer_name.upper()]
            registry = BehaviorRegistry(default_dispatch_layer=layer)
            for func_spec in funcs:
                if isinstance(func_spec, tuple):
                    func, task = func_spec
                else:
                    func, task = func_spec, None
                registry.register(func=func, task=task)
            registries.append(registry)
        return SimpleNamespace(
            get_registries=lambda: registries,
            get_inline_behaviors=lambda: [],
        )

    return _make


@pytest.fixture(autouse=True)
def clean_global_dispatch() -> None:
    """Keep global dispatch state isolated between tests."""
    yield
    from tangl.core.dispatch import dispatch

    dispatch.clear()


@pytest.fixture(autouse=True)
def ensure_no_ambient_ctx() -> None:
    """Fail fast if tests leak ambient context."""
    yield
    from tangl.core.ctx import get_ctx

    assert get_ctx() is None, "Ambient ctx leaked between tests"


@pytest.fixture(autouse=True)
def clear_token_singletons() -> None:
    """Clear token test singletons and wrapper cache around each test."""
    for cls in [WeaponType, ArmorType, NPCType]:
        cls.clear_instances()
    Token._wrapper_cache.clear()
    yield
    for cls in [WeaponType, ArmorType, NPCType]:
        cls.clear_instances()
    Token._wrapper_cache.clear()
