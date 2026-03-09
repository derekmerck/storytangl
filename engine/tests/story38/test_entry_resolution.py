"""Tests for compile-time entry resolution and positional block wiring.

Organized by behavior:
- Entry resolution priority: authored start hints over positional fallback.
- Bare-next wiring: implicit outgoing intent resolves by block order.
- Anonymous blocks: unlabeled list-form blocks get stable synthetic labels.
- Init-time override: worlds may replace the compiled entry at story creation.
"""
from __future__ import annotations

from typing import Any

from tangl.story import MenuBlock
from tangl.story.fabula import StoryCompiler, World
from tangl.story.fabula.types import StoryInitResult


def _compile(data: dict[str, Any]) -> Any:
    return StoryCompiler().compile(data)


def _entry_ids(data: dict[str, Any]) -> list[str]:
    return _compile(data).entry_template_ids


def _materialize(data: dict[str, Any]) -> StoryInitResult:
    bundle = _compile(data)
    world = World(label=data.get("label", "test"), bundle=bundle)
    return world.create_story("test")


class TestEntryResolutionPriority:
    """Tests for compile-time entry resolution priority."""

    def test_explicit_start_at_wins(self) -> None:
        data = {
            "label": "test",
            "metadata": {"start_at": "s.second"},
            "scenes": {
                "s": {
                    "blocks": {
                        "first": {"content": "A", "actions": []},
                        "second": {"content": "B", "actions": []},
                    }
                }
            },
        }

        assert _entry_ids(data) == ["s.second"]

    def test_start_at_list(self) -> None:
        data = {
            "label": "test",
            "metadata": {"start_at": ["s.a", "s.b"]},
            "scenes": {
                "s": {
                    "blocks": {
                        "a": {"content": "A", "actions": []},
                        "b": {"content": "B", "actions": []},
                    }
                }
            },
        }

        assert _entry_ids(data) == ["s.a", "s.b"]

    def test_tag_start_resolves(self) -> None:
        data = {
            "label": "test",
            "scenes": {
                "s": {
                    "blocks": {
                        "intro": {"content": "A", "actions": []},
                        "tagged": {"content": "B", "tags": ["start"], "actions": []},
                    }
                }
            },
        }

        assert _entry_ids(data) == ["s.tagged"]

    def test_tag_entry_resolves(self) -> None:
        data = {
            "label": "test",
            "scenes": {
                "s": {
                    "blocks": {
                        "first": {"content": "A", "actions": []},
                        "home": {"content": "B", "tags": ["entry"], "actions": []},
                    }
                }
            },
        }

        assert _entry_ids(data) == ["s.home"]

    def test_locals_is_start_resolves(self) -> None:
        data = {
            "label": "test",
            "scenes": {
                "s": {
                    "blocks": {
                        "a": {"content": "A", "actions": []},
                        "b": {"content": "B", "locals": {"is_start": True}, "actions": []},
                    }
                }
            },
        }

        assert _entry_ids(data) == ["s.b"]

    def test_label_start_resolves_case_insensitive(self) -> None:
        data = {
            "label": "test",
            "scenes": {
                "s": {
                    "blocks": {
                        "preamble": {"content": "A", "actions": []},
                        "Start": {"content": "B", "actions": []},
                        "finale": {"content": "C", "actions": []},
                    }
                }
            },
        }

        assert _entry_ids(data) == ["s.Start"]

    def test_positional_fallback(self) -> None:
        data = {
            "label": "test",
            "scenes": {
                "s": {
                    "blocks": {
                        "alpha": {"content": "A", "actions": []},
                        "beta": {"content": "B", "actions": []},
                    }
                }
            },
        }

        assert _entry_ids(data) == ["s.alpha"]

    def test_explicit_start_at_beats_tag(self) -> None:
        data = {
            "label": "test",
            "metadata": {"start_at": "s.alpha"},
            "scenes": {
                "s": {
                    "blocks": {
                        "alpha": {"content": "A", "actions": []},
                        "tagged": {"content": "B", "tags": ["start"], "actions": []},
                    }
                }
            },
        }

        assert _entry_ids(data) == ["s.alpha"]

    def test_empty_scenes_returns_empty(self) -> None:
        assert _entry_ids({"label": "test", "scenes": {}}) == []


class TestBareNextResolution:
    """Tests for implicit positional successor resolution."""

    def test_bare_action_resolves_to_next_block(self) -> None:
        data = {
            "label": "test",
            "scenes": {
                "s": {
                    "blocks": {
                        "a": {"content": "First", "actions": [{"text": "Continue"}]},
                        "b": {"content": "Second", "actions": []},
                    }
                }
            },
        }

        result = _materialize(data)
        members = list(result.graph.members.values())
        block_a = next(member for member in members if getattr(member, "label", "") == "a")
        block_b = next(member for member in members if getattr(member, "label", "") == "b")

        edges_from_a = [
            member
            for member in members
            if getattr(member, "destination_id", None) is not None
            and getattr(member, "source_id", None) == block_a.uid
        ]
        assert len(edges_from_a) == 1
        assert edges_from_a[0].destination_id == block_b.uid

    def test_bare_continue_resolves_to_next_block(self) -> None:
        data = {
            "label": "test",
            "scenes": {
                "s": {
                    "blocks": {
                        "a": {"content": "First", "continues": [{}]},
                        "b": {"content": "Second", "actions": []},
                    }
                }
            },
        }

        result = _materialize(data)
        members = list(result.graph.members.values())
        block_a = next(member for member in members if getattr(member, "label", "") == "a")
        block_b = next(member for member in members if getattr(member, "label", "") == "b")

        edges_from_a = [
            member
            for member in members
            if getattr(member, "destination_id", None) is not None
            and getattr(member, "source_id", None) == block_a.uid
        ]
        assert len(edges_from_a) == 1
        assert edges_from_a[0].destination_id == block_b.uid

    def test_mixed_explicit_and_bare_actions(self) -> None:
        data = {
            "label": "test",
            "scenes": {
                "s": {
                    "blocks": {
                        "a": {
                            "content": "Choose",
                            "actions": [
                                {"text": "Jump ahead", "successor": "c"},
                                {"text": "Continue normally"},
                            ],
                        },
                        "b": {"content": "Linear next"},
                        "c": {"content": "Jumped to"},
                    }
                }
            },
        }

        result = _materialize(data)
        members = list(result.graph.members.values())
        block_a = next(member for member in members if getattr(member, "label", "") == "a")
        block_b = next(member for member in members if getattr(member, "label", "") == "b")
        block_c = next(member for member in members if getattr(member, "label", "") == "c")

        edges_from_a = [
            member
            for member in members
            if getattr(member, "destination_id", None) is not None
            and getattr(member, "source_id", None) == block_a.uid
        ]
        destinations = {edge.destination_id for edge in edges_from_a}
        assert block_b.uid in destinations
        assert block_c.uid in destinations
        assert len(edges_from_a) == 2

    def test_explicit_actions_do_not_trigger_bare_next(self) -> None:
        data = {
            "label": "test",
            "scenes": {
                "s": {
                    "blocks": {
                        "a": {
                            "content": "Choose",
                            "actions": [{"text": "Go to c", "successor": "c"}],
                        },
                        "b": {"content": "Skipped"},
                        "c": {"content": "Target"},
                    }
                }
            },
        }

        result = _materialize(data)
        members = list(result.graph.members.values())
        block_a = next(member for member in members if getattr(member, "label", "") == "a")
        block_c = next(member for member in members if getattr(member, "label", "") == "c")

        edges_from_a = [
            member
            for member in members
            if getattr(member, "destination_id", None) is not None
            and getattr(member, "source_id", None) == block_a.uid
        ]
        assert len(edges_from_a) == 1
        assert edges_from_a[0].destination_id == block_c.uid

    def test_next_alias_resolves_to_named_target(self) -> None:
        data = {
            "label": "test",
            "scenes": {
                "s": {
                    "blocks": {
                        "a": {
                            "content": "Choose",
                            "actions": [{"content": "Go forward", "next": "b"}],
                        },
                        "b": {"content": "Target"},
                    }
                }
            },
        }

        result = _materialize(data)
        members = list(result.graph.members.values())
        block_a = next(member for member in members if getattr(member, "label", "") == "a")
        block_b = next(member for member in members if getattr(member, "label", "") == "b")
        edge = next(
            member
            for member in members
            if getattr(member, "destination_id", None) is not None
            and getattr(member, "source_id", None) == block_a.uid
        )

        assert edge.destination_id == block_b.uid
        assert getattr(edge, "text", "") == "Go forward"

    def test_bare_action_on_last_block_stays_unresolved(self) -> None:
        data = {
            "label": "test",
            "scenes": {
                "s": {
                    "blocks": {
                        "a": {"content": "First", "actions": [{"text": "Next"}]},
                        "z": {"content": "Last", "actions": [{"text": "Done"}]},
                    }
                }
            },
        }

        bundle = _compile(data)
        assert bundle.template_registry is not None

    def test_block_with_no_actions_is_terminal(self) -> None:
        data = {
            "label": "test",
            "scenes": {
                "s": {
                    "blocks": {
                        "a": {"content": "The End."},
                        "b": {"content": "Unreachable."},
                    }
                }
            },
        }

        result = _materialize(data)
        members = list(result.graph.members.values())
        block_a = next(member for member in members if getattr(member, "label", "") == "a")
        edges_from_a = [
            member
            for member in members
            if getattr(member, "destination_id", None) is not None
            and getattr(member, "source_id", None) == block_a.uid
        ]
        assert len(edges_from_a) == 0

    def test_explicit_continues_suppress_bare_next(self) -> None:
        data = {
            "label": "test",
            "scenes": {
                "s": {
                    "blocks": {
                        "a": {"content": "Continue explicitly", "continues": [{"successor": "c"}]},
                        "b": {"content": "Skipped"},
                        "c": {"content": "Target"},
                    }
                }
            },
        }

        result = _materialize(data)
        members = list(result.graph.members.values())
        block_a = next(member for member in members if getattr(member, "label", "") == "a")
        block_c = next(member for member in members if getattr(member, "label", "") == "c")

        edges_from_a = [
            member
            for member in members
            if getattr(member, "destination_id", None) is not None
            and getattr(member, "source_id", None) == block_a.uid
        ]
        assert len(edges_from_a) == 1
        assert edges_from_a[0].destination_id == block_c.uid


class TestAnonymousBlocks:
    """Tests for anonymous block labeling and reachability."""

    def test_anonymous_blocks_get_synthetic_labels(self) -> None:
        data = {
            "label": "test",
            "scenes": {
                "s": {
                    "blocks": [
                        {"label": "start", "content": "Begin", "actions": [{"text": "Go"}]},
                        {"content": "Anonymous 1", "actions": [{"text": "Continue"}]},
                        {"content": "Anonymous 2"},
                    ]
                }
            },
        }

        bundle = _compile(data)
        labels = {template.get_label() for template in bundle.template_registry.members.values()}
        anon_zero = bundle.template_registry.find_one(has_identifier="s._anon_0")

        assert "s.start" in labels
        assert "s._anon_0" in labels
        assert "s._anon_1" in labels
        assert anon_zero is not None
        assert getattr(anon_zero.payload, "is_anonymous", False) is True

    def test_bare_action_reaches_anonymous_block(self) -> None:
        data = {
            "label": "test",
            "scenes": {
                "s": {
                    "blocks": [
                        {
                            "label": "door",
                            "content": "A door.",
                            "actions": [
                                {"text": "Open the door"},
                                {"text": "Leave", "successor": "leave"},
                            ],
                        },
                        {"content": "The door creaks open.", "actions": [{"text": "Step inside"}]},
                        {"content": "You enter a dusty room."},
                        {"label": "leave", "content": "You walk away."},
                    ]
                }
            },
        }

        result = _materialize(data)
        members = list(result.graph.members.values())
        block_door = next(member for member in members if getattr(member, "label", "") == "door")
        block_anon0 = next(member for member in members if getattr(member, "label", "") == "_anon_0")
        block_anon1 = next(member for member in members if getattr(member, "label", "") == "_anon_1")
        block_leave = next(member for member in members if getattr(member, "label", "") == "leave")

        edges_door = [
            member
            for member in members
            if getattr(member, "destination_id", None) is not None
            and getattr(member, "source_id", None) == block_door.uid
        ]
        destinations = {edge.destination_id for edge in edges_door}
        assert block_anon0.uid in destinations
        assert block_leave.uid in destinations

        edges_anon0 = [
            member
            for member in members
            if getattr(member, "destination_id", None) is not None
            and getattr(member, "source_id", None) == block_anon0.uid
        ]
        assert len(edges_anon0) == 1
        assert edges_anon0[0].destination_id == block_anon1.uid


class TestInitTimeOverride:
    """Tests for init-time world entry override hooks."""

    def test_default_namespace_none(self) -> None:
        data = {
            "label": "test",
            "metadata": {"start_at": "s.a"},
            "scenes": {
                "s": {
                    "blocks": {
                        "a": {"content": "Start", "actions": []},
                        "b": {"content": "Other", "actions": []},
                    }
                }
            },
        }

        world = World(label="test", bundle=_compile(data))
        result = world.create_story("test")
        entry = result.graph.get(result.graph.initial_cursor_id)
        assert entry.label == "a"

    def test_namespace_passed_without_override(self) -> None:
        data = {
            "label": "test",
            "metadata": {"start_at": "s.a"},
            "scenes": {
                "s": {
                    "blocks": {
                        "a": {"content": "Start", "actions": []},
                        "b": {"content": "Other", "actions": []},
                    }
                }
            },
        }

        world = World(label="test", bundle=_compile(data))
        result = world.create_story("test", namespace={"user": None})
        entry = result.graph.get(result.graph.initial_cursor_id)
        assert entry.label == "a"

    def test_subclass_override_changes_entry(self) -> None:
        class TestWorld(World):
            def _resolve_entry_override(self, graph, namespace):
                target_label = namespace.get("start_at_label")
                if target_label is None:
                    return None
                for member in graph.members.values():
                    if getattr(member, "label", None) == target_label:
                        return member.uid
                return None

        data = {
            "label": "test",
            "metadata": {"start_at": "s.a"},
            "scenes": {
                "s": {
                    "blocks": {
                        "a": {"content": "Default start", "actions": []},
                        "b": {"content": "Override target", "actions": []},
                    }
                }
            },
        }

        world = TestWorld(label="test_override", bundle=_compile(data))
        result = world.create_story("test", namespace={"start_at_label": "b"})
        entry = result.graph.get(result.graph.initial_cursor_id)
        assert entry.label == "b"
        assert result.entry_ids == [entry.uid]
        assert result.graph.initial_cursor_ids == [entry.uid]

    def test_override_returning_none_uses_default(self) -> None:
        class NullOverride(World):
            def _resolve_entry_override(self, graph, namespace):
                return None

        data = {
            "label": "test",
            "metadata": {"start_at": "s.first"},
            "scenes": {"s": {"blocks": {"first": {"content": "Hi", "actions": []}}}},
        }

        world = NullOverride(label="null_override", bundle=_compile(data))
        result = world.create_story("test", namespace={"user": "nobody"})
        entry = result.graph.get(result.graph.initial_cursor_id)
        assert entry.label == "first"


class TestMenuBlockScaffold:
    """Tests for preserving menu metadata in compiled runtime payloads."""

    def test_menu_block_kind_preserves_menu_items(self) -> None:
        bundle = _compile(
            {
                "label": "menu_test",
                "scenes": {
                    "s": {
                        "blocks": [
                            {
                                "label": "hub",
                                "kind": "MenuBlock",
                                "menu_items": {
                                    "has_tags": ["foo"],
                                    "return_when_done": True,
                                },
                            }
                        ]
                    }
                },
            }
        )

        menu_template = bundle.template_registry.find_one(has_identifier="s.hub")
        assert menu_template is not None
        assert isinstance(menu_template.payload, MenuBlock)
        assert menu_template.payload.menu_items == {
            "has_tags": ["foo"],
            "return_when_done": True,
        }
