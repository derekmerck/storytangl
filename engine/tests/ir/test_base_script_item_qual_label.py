"""Tests for BaseScriptItem.qual_label identifier property."""

from __future__ import annotations

from tangl.ir.core_ir.base_script_model import BaseScriptItem
from tangl.ir.story_ir.story_script_models import ScopeSelector


def test_global_template_qual_label_equals_plain_label() -> None:
    """Templates without scope constraints should use plain label."""

    template = BaseScriptItem(label="guard")

    assert template.qual_label == "guard"
    assert template.has_identifier("guard")


def test_scoped_template_qual_label_includes_parent() -> None:
    """Scene-scoped templates should prefix parent label."""

    template = BaseScriptItem(label="start", scope=ScopeSelector(parent_label="scene1"))

    assert template.qual_label == "scene1.start"
    assert template.has_identifier("scene1.start")
    assert template.has_identifier("start")


def test_qual_label_distinguishes_same_label_different_scopes() -> None:
    """Two templates with same label but different scopes have different qual_labels."""

    template1 = BaseScriptItem(label="start", scope=ScopeSelector(parent_label="scene1"))
    template2 = BaseScriptItem(label="start", scope=ScopeSelector(parent_label="scene2"))

    assert template1.qual_label == "scene1.start"
    assert template2.qual_label == "scene2.start"
    assert template1.qual_label != template2.qual_label


def test_qual_label_appears_in_identifiers() -> None:
    """qual_label should be discoverable via get_identifiers()."""

    template = BaseScriptItem(label="guard", scope=ScopeSelector(parent_label="castle"))

    identifiers = set(template.get_identifiers())
    assert "castle.guard" in identifiers
    assert "guard" in identifiers
