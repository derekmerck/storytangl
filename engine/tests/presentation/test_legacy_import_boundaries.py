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
    "StoryInfoRequest",
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


@pytest.mark.parametrize("module_name", ("tangl.journal.fragments", "tangl.service.response"))
def test_former_journal_and_service_presentation_attributes_do_not_resolve(
    module_name: str,
) -> None:
    module = import_module(module_name)

    assert all(not hasattr(module, name) for name in MOVED_NAMES)
