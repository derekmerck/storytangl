"""Deleted presentation import locations fail loudly."""

from __future__ import annotations

from importlib import import_module

import pytest


MOVED_NAMES = (
    "Accepts",
    "Blocker",
    "UIHints",
    "PresentationHints",
    "StagingHints",
    "KvRow",
    "PrimitiveValue",
    "UxEvent",
    "GrammarHint",
    "GrammarNoun",
    "GrammarVerb",
    "InfoAffordance",
    "InfoState",
    "ProjectionRequest",
    "ProjectedState",
    "ProjectedSection",
    "ScalarValue",
    "KvListValue",
    "ProjectedItem",
    "ItemListValue",
    "TableValue",
    "BadgeListValue",
    "SectionValue",
)


def test_deleted_journal_intent_module_cannot_import() -> None:
    with pytest.raises(ModuleNotFoundError):
        import_module("tangl.journal.intent")


def test_deleted_service_projector_module_cannot_import() -> None:
    with pytest.raises(ModuleNotFoundError):
        import_module("tangl.service.story_info")


@pytest.mark.parametrize("module_name", ("tangl.journal.fragments", "tangl.service.response"))
def test_former_journal_and_service_presentation_attributes_do_not_resolve(
    module_name: str,
) -> None:
    module = import_module(module_name)

    assert all(not hasattr(module, name) for name in MOVED_NAMES)


def test_service_no_longer_exports_presentation_registration_or_projectors() -> None:
    service = import_module("tangl.service")

    assert all(
        not hasattr(service, name)
        for name in (
            "DefaultStoryInfoProjector",
            "StoryInfoProjector",
            "on_advertise_info_channels",
            "on_get_story_info",
        )
    )
