"""Tests for template metadata flags.

Organized by functionality:
- Declared instance flags on templates.
- Script-only containers that omit parent assignment.
"""

from __future__ import annotations

from tangl.core.factory import HierarchicalTemplate, Template


# ============================================================================
# Declared instance flags
# ============================================================================

class TestTemplateInstanceFlags:
    """Tests for template instance declaration flags."""

    def test_declares_instance_flag(self) -> None:
        """Templates can be marked as declaring an instance."""

        template = Template(label="block1", declares_instance=True)

        assert template.declares_instance is True


# ============================================================================
# Script-only containers
# ============================================================================

class TestScriptOnlyContainers:
    """Tests for script-only container behavior."""

    def test_script_only_prevents_parent_assignment(self) -> None:
        """Script-only containers should not assign parents to children."""

        root = HierarchicalTemplate(
            label="packaging",
            script_only=True,
            children={
                "actual_template": HierarchicalTemplate(label="shop")
            },
        )

        shop = root.children["actual_template"]

        assert shop.parent is None
        assert shop.path == "shop"
