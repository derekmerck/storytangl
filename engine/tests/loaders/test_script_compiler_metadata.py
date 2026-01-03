"""Tests for script compiler metadata flags.

Organized by functionality:
- Declared instances in scenes and blocks.
- Archetype templates in the templates section.
"""

from __future__ import annotations

from tangl.loaders.compilers.script_compiler import ScriptCompiler


# ============================================================================
# Declared instance marking
# ============================================================================

class TestScriptCompilerDeclaredInstances:
    """Tests for declared instance metadata during compilation."""

    def test_scenes_marked_as_declared_instances(self) -> None:
        """Scenes and blocks should be marked declares_instance=True."""

        script_data = {
            "label": "test",
            "metadata": {"title": "Test", "author": "Tests"},
            "scenes": {
                "scene1": {
                    "label": "scene1",
                    "blocks": {
                        "start": {
                            "label": "start",
                            "obj_cls": "tangl.story.episode.block.Block",
                        }
                    },
                }
            },
        }

        compiler = ScriptCompiler()
        manager = compiler.compile(script_data)

        scene_template = manager.template_factory.find_one(label="scene1")
        assert scene_template is not None
        assert scene_template.declares_instance is True

        block_template = manager.template_factory.find_one(label="start")
        assert block_template is not None
        assert block_template.declares_instance is True


class TestScriptCompilerTemplateArchetypes:
    """Tests for template archetype marking during compilation."""

    def test_templates_marked_as_archetypes(self) -> None:
        """Templates section should mark declares_instance=False."""

        script_data = {
            "label": "test",
            "metadata": {"title": "Test", "author": "Tests"},
            "templates": {
                "guard": {
                    "obj_cls": "tangl.story.concepts.actor.actor.Actor",
                }
            },
            "scenes": {},
        }

        compiler = ScriptCompiler()
        manager = compiler.compile(script_data)

        template = manager.template_factory.find_one(label="guard")
        assert template is not None
        assert template.declares_instance is False
