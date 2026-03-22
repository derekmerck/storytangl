"""End-to-end traversal playthrough tests for story + vm ledger.

These are the story replacements for the legacy ``test_simple_story.py``
and ``test_branching_playthrough.py`` test modules.  They exercise the full
pipeline from script compilation through ``World.from_script_data`` →
``create_story`` (EAGER) → ``Ledger.resolve_choice``, validating:

- Linear story traversal (cursor advances correctly on each step)
- Branching story traversal (each branch lands at the right node)
- Fragment emission at each cursor position (ContentFragment, ChoiceFragment)
- Ledger step counter increments per ``resolve_choice`` call
- Dead-end detection (no choices available at terminal block)
- Multi-step traversal order is deterministic across identical scripts

These tests are primarily EAGER traversal coverage, plus one LAZY cross-scene
regression for Part A destination canonicalization.

See Also
--------
- ``tangl.story.fabula.World.from_script_data``
- ``tangl.vm.runtime.ledger.Ledger.resolve_choice``
- ``tangl.vm.dispatch.do_journal``
"""

from __future__ import annotations

import pytest

from tangl.core import EntityTemplate, Selector, TemplateRegistry
from tangl.story import InitMode, World
from tangl.story.episode import Action, Block, Scene
from tangl.story.fragments import ChoiceFragment, ContentFragment
from tangl.story.story_graph import StoryGraph
from tangl.vm import Ledger
from tangl.vm import Dependency, Requirement
from tangl.vm.dispatch import do_journal

import tangl.story  # noqa: F401 – ensure story journal/phase handlers are registered


# ---------------------------------------------------------------------------
# Shared script builders
# ---------------------------------------------------------------------------

def _linear_script() -> dict:
    return {
        "label": "linear_world",
        "metadata": {
            "title": "Linear",
            "author": "Tests",
            "start_at": "chapter.intro",
        },
        "scenes": {
            "chapter": {
                "blocks": {
                    "intro": {
                        "content": "You stand at the entrance.",
                        "actions": [{"text": "Enter", "successor": "hall"}],
                    },
                    "hall": {
                        "content": "You are in the great hall.",
                        "actions": [{"text": "Continue", "successor": "end"}],
                    },
                    "end": {
                        "content": "You have reached the end.",
                    },
                }
            }
        },
    }


def _branching_script() -> dict:
    return {
        "label": "branching_world",
        "metadata": {
            "title": "Branching",
            "author": "Tests",
            "start_at": "root.start",
        },
        "scenes": {
            "root": {
                "blocks": {
                    "start": {
                        "content": "Choose your path.",
                        "actions": [
                            {"text": "Go left", "successor": "left_end"},
                            {"text": "Go right", "successor": "right_end"},
                        ],
                    },
                    "left_end": {"content": "You went left."},
                    "right_end": {"content": "You went right."},
                }
            }
        },
    }


def _state_script() -> dict:
    """Story with a globals-initialised counter visible in content templates."""
    return {
        "label": "state_world",
        "metadata": {
            "title": "State",
            "author": "Tests",
            "start_at": "game.begin",
        },
        "globals": {"gold": 10},
        "scenes": {
            "game": {
                "blocks": {
                    "begin": {
                        "content": "You have {gold} gold.",
                        "actions": [{"text": "Continue", "successor": "middle"}],
                    },
                    "middle": {
                        "content": "Onwards.",
                        "actions": [{"text": "Finish", "successor": "fin"}],
                    },
                    "fin": {"content": "Done."},
                }
            }
        },
    }


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def linear_ledger() -> Ledger:
    world = World.from_script_data(script_data=_linear_script())
    result = world.create_story("linear_play", init_mode=InitMode.EAGER)
    return Ledger.from_graph(result.graph, entry_id=result.graph.initial_cursor_id)


@pytest.fixture()
def branching_ledger() -> Ledger:
    world = World.from_script_data(script_data=_branching_script())
    result = world.create_story("branching_play", init_mode=InitMode.EAGER)
    return Ledger.from_graph(result.graph, entry_id=result.graph.initial_cursor_id)


# ---------------------------------------------------------------------------
# Linear traversal
# ---------------------------------------------------------------------------

class TestLinearTraversal:
    def test_initial_cursor_is_entry_block(self, linear_ledger: Ledger) -> None:
        assert linear_ledger.cursor is not None
        assert linear_ledger.cursor.label == "intro"

    def test_step_counter_starts_at_zero(self, linear_ledger: Ledger) -> None:
        assert linear_ledger.step == 0

    def test_resolve_choice_advances_cursor(self, linear_ledger: Ledger) -> None:
        action = _get_single_action(linear_ledger)
        linear_ledger.resolve_choice(action.uid)
        assert linear_ledger.cursor.label == "hall"

    def test_step_counter_increments_per_resolve(self, linear_ledger: Ledger) -> None:
        action = _get_single_action(linear_ledger)
        linear_ledger.resolve_choice(action.uid)
        assert linear_ledger.step == 1

    def test_second_step_advances_to_end(self, linear_ledger: Ledger) -> None:
        for _ in range(2):
            action = _get_single_action(linear_ledger)
            linear_ledger.resolve_choice(action.uid)
        assert linear_ledger.cursor.label == "end"

    def test_terminal_block_has_no_available_choices(self, linear_ledger: Ledger) -> None:
        for _ in range(2):
            action = _get_single_action(linear_ledger)
            linear_ledger.resolve_choice(action.uid)

        actions = list(
            linear_ledger.cursor.edges_out(Selector(has_kind=Action, trigger_phase=None))
        )
        assert actions == []

    def test_journal_emits_content_at_each_step(self, linear_ledger: Ledger) -> None:
        from tangl.vm.runtime.frame import PhaseCtx

        labels_seen: list[str] = []
        for _ in range(2):
            ctx = PhaseCtx(
                graph=linear_ledger.graph,
                cursor_id=linear_ledger.cursor_id,
            )
            fragments = do_journal(linear_ledger.cursor, ctx=ctx)
            content = next((f for f in fragments if isinstance(f, ContentFragment)), None)
            assert content is not None
            labels_seen.append(linear_ledger.cursor.label)
            action = _get_single_action(linear_ledger)
            linear_ledger.resolve_choice(action.uid)

        assert labels_seen == ["intro", "hall"]

    def test_traversal_is_deterministic(self) -> None:
        """Same script produces same traversal path on two independent ledgers."""
        def _run(label: str) -> list[str]:
            script = _linear_script()
            script["label"] = label
            world = World.from_script_data(script_data=script)
            result = world.create_story("det_play", init_mode=InitMode.EAGER)
            ledger = Ledger.from_graph(result.graph, entry_id=result.graph.initial_cursor_id)
            path: list[str] = [ledger.cursor.label]
            while True:
                actions = list(
                    ledger.cursor.edges_out(Selector(has_kind=Action, trigger_phase=None))
                )
                if not actions:
                    break
                ledger.resolve_choice(actions[0].uid)
                path.append(ledger.cursor.label)
            return path

        assert _run("linear_world_a") == _run("linear_world_b")


# ---------------------------------------------------------------------------
# Branching traversal
# ---------------------------------------------------------------------------

class TestBranchingTraversal:
    def test_left_choice_reaches_left_end(self, branching_ledger: Ledger) -> None:
        action = _get_action_by_text(branching_ledger, "Go left")
        branching_ledger.resolve_choice(action.uid)
        assert branching_ledger.cursor.label == "left_end"

    def test_right_choice_reaches_right_end(self) -> None:
        world = World.from_script_data(script_data=_branching_script())
        result = world.create_story("branch_right", init_mode=InitMode.EAGER)
        ledger = Ledger.from_graph(result.graph, entry_id=result.graph.initial_cursor_id)

        action = _get_action_by_text(ledger, "Go right")
        ledger.resolve_choice(action.uid)
        assert ledger.cursor.label == "right_end"

    def test_start_block_has_two_choices(self, branching_ledger: Ledger) -> None:
        actions = list(
            branching_ledger.cursor.edges_out(Selector(has_kind=Action, trigger_phase=None))
        )
        assert len(actions) == 2

    def test_choice_texts_are_distinct(self, branching_ledger: Ledger) -> None:
        texts = {
            a.text
            for a in branching_ledger.cursor.edges_out(
                Selector(has_kind=Action, trigger_phase=None)
            )
        }
        assert "Go left" in texts
        assert "Go right" in texts

    def test_both_branches_are_marked_available(self, branching_ledger: Ledger) -> None:
        from tangl.vm.runtime.frame import PhaseCtx

        ctx = PhaseCtx(
            graph=branching_ledger.graph,
            cursor_id=branching_ledger.cursor_id,
        )
        fragments = do_journal(branching_ledger.cursor, ctx=ctx)
        choices = [f for f in fragments if isinstance(f, ChoiceFragment)]
        assert all(c.available for c in choices)


# ---------------------------------------------------------------------------
# Story globals / namespace
# ---------------------------------------------------------------------------

class TestStoryGlobals:
    def test_globals_initialised_in_story_locals(self) -> None:
        world = World.from_script_data(script_data=_state_script())
        result = world.create_story("state_play", init_mode=InitMode.EAGER)
        assert result.graph.locals.get("gold") == 10

    def test_content_template_renders_with_globals(self) -> None:
        world = World.from_script_data(script_data=_state_script())
        result = world.create_story("state_render", init_mode=InitMode.EAGER)
        ledger = Ledger.from_graph(result.graph, entry_id=result.graph.initial_cursor_id)

        from tangl.vm.runtime.frame import PhaseCtx

        ctx = PhaseCtx(graph=ledger.graph, cursor_id=ledger.cursor_id)
        fragments = do_journal(ledger.cursor, ctx=ctx)

        content = next((f for f in fragments if isinstance(f, ContentFragment)), None)
        assert content is not None
        assert "10" in content.content  # {gold} rendered


# ---------------------------------------------------------------------------
# Multi-scene world
# ---------------------------------------------------------------------------

class TestMultiScene:
    """EAGER mode wires cross-scene actions correctly."""

    def test_cross_scene_action_advances_cursor(self) -> None:
        script = {
            "label": "multi_scene_world",
            "metadata": {
                "title": "Multi Scene",
                "author": "Tests",
                "start_at": "forest.entrance",
            },
            "scenes": {
                "forest": {
                    "blocks": {
                        "entrance": {
                            "content": "You are in the forest.",
                            "actions": [{"text": "Enter cave", "successor": "cave.mouth"}],
                        }
                    }
                },
                "cave": {
                    "blocks": {
                        "mouth": {"content": "You enter the dark cave."}
                    }
                },
            },
        }

        world = World.from_script_data(script_data=script)
        result = world.create_story("multi_play", init_mode=InitMode.EAGER)
        ledger = Ledger.from_graph(result.graph, entry_id=result.graph.initial_cursor_id)

        assert ledger.cursor.label == "entrance"
        action = _get_single_action(ledger)
        ledger.resolve_choice(action.uid)
        assert ledger.cursor.label == "mouth"


# ---------------------------------------------------------------------------
# Selection-time provisioning
# ---------------------------------------------------------------------------

class TestSelectionTimeProvisioning:
    def test_unresolved_but_viable_choice_provisions_then_traverses(self) -> None:
        graph = StoryGraph(label="selection_time")
        start = Block(label="start", content="Start")
        graph.add(start)
        action = Action(predecessor_id=start.uid, text="Go end")
        graph.add(action)
        destination_req = Requirement(
            has_kind=Block,
            has_identifier="end",
            authored_path="end",
            is_qualified=False,
            hard_requirement=True,
        )
        dep = Dependency(
            registry=graph,
            predecessor_id=action.uid,
            label="destination",
            requirement=destination_req,
        )

        templates = TemplateRegistry(label="selection_time_templates")
        EntityTemplate(
            label="end",
            payload=Block(label="end", content="Done"),
            registry=templates,
        )
        graph.factory = templates
        graph.initial_cursor_id = start.uid

        ledger = Ledger.from_graph(graph=graph, entry_id=start.uid)
        ledger.resolve_choice(action.uid)

        assert ledger.cursor.label == "end"
        assert dep.satisfied is True
        assert dep.provider is ledger.cursor


# ---------------------------------------------------------------------------
# LAZY cross-scene regression
# ---------------------------------------------------------------------------

class TestLazyCrossSceneProvisioning:
    def test_bare_scene_successor_provisions_scene_at_root_scope(self) -> None:
        script = {
            "label": "lazy_cross_scene_world",
            "metadata": {
                "title": "Lazy Cross Scene",
                "author": "Tests",
                "start_at": "scene1.start",
            },
            "scenes": {
                "scene1": {
                    "blocks": {
                        "start": {
                            "content": "Start",
                            "actions": [{"text": "Go", "successor": "scene2"}],
                        }
                    }
                },
                "scene2": {
                    "blocks": {
                        "entry": {"content": "Entry"},
                    }
                },
            },
        }

        world = World.from_script_data(script_data=script)
        result = world.create_story("lazy_cross_scene_story", init_mode=InitMode.LAZY)
        ledger = Ledger.from_graph(result.graph, entry_id=result.graph.initial_cursor_id)

        action = _get_single_action(ledger)
        ledger.resolve_choice(action.uid)

        scene2 = next(
            (
                node
                for node in ledger.graph.values()
                if isinstance(node, Scene) and node.label == "scene2"
            ),
            None,
        )
        assert scene2 is not None
        assert scene2.parent is None

        nested_scene2 = next(
            (
                node
                for node in ledger.graph.values()
                if isinstance(node, Scene)
                and node.label == "scene2"
                and node.parent is not None
                and getattr(node.parent, "label", None) == "scene1"
            ),
            None,
        )
        assert nested_scene2 is None

    def test_qualified_scene_block_successor_provisions_and_binds_entry(self) -> None:
        script = {
            "label": "lazy_cross_scene_qualified_world",
            "metadata": {
                "title": "Lazy Cross Scene Qualified",
                "author": "Tests",
                "start_at": "scene1.start",
            },
            "scenes": {
                "scene1": {
                    "blocks": {
                        "start": {
                            "content": "Start",
                            "actions": [{"text": "Go", "successor": "scene2.entry"}],
                        }
                    }
                },
                "scene2": {
                    "blocks": {
                        "entry": {"content": "Entry"},
                    }
                },
            },
        }

        world = World.from_script_data(script_data=script)
        result = world.create_story("lazy_cross_scene_qualified_story", init_mode=InitMode.LAZY)
        ledger = Ledger.from_graph(result.graph, entry_id=result.graph.initial_cursor_id)

        action = _get_single_action(ledger)
        ledger.resolve_choice(action.uid)

        assert ledger.cursor.label == "entry"

        scene2 = next(
            (
                node
                for node in ledger.graph.values()
                if isinstance(node, Scene) and node.label == "scene2"
            ),
            None,
        )
        assert scene2 is not None

        entry_block = next(
            (
                node
                for node in ledger.graph.values()
                if isinstance(node, Block)
                and node.label == "entry"
                and getattr(node.parent, "uid", None) == scene2.uid
            ),
            None,
        )
        assert entry_block is not None
        assert scene2.source_id == entry_block.uid
        assert scene2.sink_id == entry_block.uid

# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _get_single_action(ledger: Ledger) -> Action:
    actions = list(ledger.cursor.edges_out(Selector(has_kind=Action, trigger_phase=None)))
    assert len(actions) >= 1, f"No actions at cursor '{ledger.cursor.label}'"
    return actions[0]


def _get_action_by_text(ledger: Ledger, text: str) -> Action:
    actions = list(ledger.cursor.edges_out(Selector(has_kind=Action, trigger_phase=None)))
    matched = [a for a in actions if a.text == text]
    assert matched, f"No action with text '{text}' at cursor '{ledger.cursor.label}'"
    return matched[0]
