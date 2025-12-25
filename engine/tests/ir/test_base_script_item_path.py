"""Tests for BaseScriptItem.path identifier property."""

from __future__ import annotations

from tangl.ir.core_ir.base_script_model import BaseScriptItem
# from tangl.ir.story_ir.story_script_models import ScopeSelector

# todo: merge with template tests, nothing script-ish


def test_global_template_path_equals_plain_label() -> None:
    """Templates without scope constraints should use plain label."""

    template = BaseScriptItem(label="guard")

    assert template.path == "guard"
    assert template.has_identifier("guard")


def test_scoped_template_path_includes_parent() -> None:
    """Scene-scoped templates should prefix parent label."""

    parent = BaseScriptItem(label="scene1")
    template = BaseScriptItem(label="start", parent=parent)

    assert template.path == "scene1.start"
    # todo: is the path an identifier?  I don't think so, unless we admit that it's not unique (actor named foo.bar, scene named foo.bar, etc.)
    # assert template.has_identifier("scene1.start")
    assert template.has_identifier("start")


def test_path_distinguishes_same_label_different_scopes() -> None:
    """Two templates with same label but different scopes have different paths."""

    parent = BaseScriptItem(label="scene1")
    template1 = BaseScriptItem(label="start", parent=parent)
    parent = BaseScriptItem(label="scene2")
    template2 = BaseScriptItem(label="start", parent=parent)

    assert template1.path == "scene1.start"
    assert template2.path == "scene2.start"
    assert template1.path != template2.path


def test_path_appears_in_identifiers() -> None:
    """path should be discoverable via get_identifiers()."""

    parent = BaseScriptItem(label="castle")
    template = BaseScriptItem(label="guard", parent=parent)

    identifiers = set(template.get_identifiers())
    # assert "castle.guard" in identifiers
    assert "guard" in identifiers
