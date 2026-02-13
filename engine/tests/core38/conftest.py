"""Shared fixtures and helper classes for core38 trait tests."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from pydantic import Field

from tangl.core38.bases import (
    HasContent,
    HasIdentity,
    HasOrder,
    HasState,
    Unstructurable,
    is_identifier,
)


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
    from tangl.core38.behavior import BehaviorRegistry

    registry = BehaviorRegistry()
    ctx = SimpleNamespace(
        get_registries=lambda: [registry],
        get_inline_behaviors=lambda: [],
    )
    return ctx, registry


@pytest.fixture(autouse=True)
def clean_global_dispatch() -> None:
    """Keep global dispatch state isolated between tests."""
    yield
    from tangl.core38.dispatch import dispatch

    dispatch.clear()


@pytest.fixture(autouse=True)
def ensure_no_ambient_ctx() -> None:
    """Fail fast if tests leak ambient context."""
    yield
    from tangl.core38.ctx import get_ctx

    assert get_ctx() is None, "Ambient ctx leaked between tests"
