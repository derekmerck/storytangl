"""Tests for world start address resolution.

Organized by functionality:
- Explicit start address metadata.
- Fallback start address selection.
- Address normalization consistency.
"""

from __future__ import annotations

import logging

import pytest

from .conftest import build_world


# ============================================================================
# Start address resolution
# ============================================================================


class TestWorldStartAddress:
    """Tests for start address resolution behavior."""

    def test_world_with_explicit_start_at(self) -> None:
        """Explicit start_at should be used."""

        script = {
            "label": "test",
            "metadata": {
                "title": "Test",
                "author": "Test",
                "start_at": "scene2.middle",
            },
            "scenes": {
                "scene1": {"blocks": {"start": {"obj_cls": "Block"}}},
                "scene2": {"blocks": {"middle": {"obj_cls": "Block"}}},
            },
        }
        world = build_world(script)
        assert world._get_start_address() == "scene2.middle"

    def test_world_without_start_at_uses_fallback(self, caplog: pytest.LogCaptureFixture) -> None:
        """Missing start_at should use lexicographically smallest leaf."""

        script = {
            "label": "test",
            "metadata": {"title": "Test", "author": "Test"},
            "scenes": {
                "prologue": {"blocks": {"intro": {"obj_cls": "Block"}}},
                "chapter1": {"blocks": {"start": {"obj_cls": "Block"}}},
            },
        }

        world = build_world(script)

        with caplog.at_level(logging.WARNING):
            start_addr = world._get_start_address()

        assert start_addr == "chapter1.start"
        assert "No start_at specified" in caplog.text
        assert "chapter1.start" in caplog.text

    def test_world_without_start_at_and_no_templates_fails(self) -> None:
        """No start_at and no templates should raise a clear error."""

        script = {
            "label": "test",
            "metadata": {"title": "Test", "author": "Test"},
            "templates": {},
            "scenes": {},
        }

        world = build_world(script)

        with pytest.raises(ValueError, match="Cannot determine starting point"):
            world._get_start_address()

    def test_normalization_consistency(self, caplog: pytest.LogCaptureFixture) -> None:
        """Leaf detection should work in normalized space."""

        script = {
            "label": "story",
            "metadata": {"title": "Test", "author": "Test"},
            "scenes": {
                "scene1": {"blocks": {"start": {"obj_cls": "Block"}}},
            },
        }

        world = build_world(script)

        with caplog.at_level(logging.WARNING):
            start_addr = world._get_start_address()

        assert start_addr == "scene1.start"
        assert not start_addr.startswith("story.")
