"""Canonical cardinal-story projection from compiled template bundles."""

from __future__ import annotations

import json
from enum import Enum
from pathlib import Path
from typing import Any
from uuid import UUID

import yaml

from tangl.core import Selector
from tangl.story import Actor, Block, Location
from tangl.story.fabula import StoryCompiler
from tangl.vm import TraversableNode


class DomainBlock(Block):
    """Importable domain block used to prove fully qualified kind recovery."""


class Tone(str, Enum):
    """Portable source enum used by the source-value projection test."""

    CALM = "calm"


def _decompile_twice(
    source: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    compiler = StoryCompiler()
    first = compiler.decompile(compiler.compile(source))
    second = compiler.decompile(compiler.compile(first))
    return first, second


def test_decompile_organizes_cardinal_story_data_and_is_portable() -> None:
    source = {
        "label": "canonical",
        "metadata": {"title": "Canonical", "start_at": "intro.open"},
        "globals": {
            "tone": Tone.CALM,
            "checkpoint": UUID("12345678-1234-5678-1234-567812345678"),
            "source_dir": Path("content/story"),
            "priorities": ("first", "second"),
            "tags": frozenset({"calm", "entry"}),
        },
        "templates": {"root_note": {"kind": TraversableNode, "content": "Note"}},
        "actors": {"guide": {"kind": Actor, "name": "Guide"}},
        "locations": {"gate": {"kind": Location, "name": "Gate"}},
        "scenes": {
            "intro": {
                "templates": {"local_note": {"content": "Local note"}},
                "blocks": {
                    "open": {"content": "Open", "actions": [{"text": "Continue"}]},
                    "close": {"content": "Close"},
                },
            }
        },
    }

    canonical, recanonical = _decompile_twice(source)

    assert canonical == recanonical
    assert list(canonical) == [
        "label",
        "metadata",
        "globals",
        "templates",
        "actors",
        "locations",
        "scenes",
    ]
    assert canonical["metadata"]["start_at"] == "intro.open"
    assert canonical["globals"] == {
        "checkpoint": "12345678-1234-5678-1234-567812345678",
        "priorities": ["first", "second"],
        "source_dir": "content/story",
        "tags": ["calm", "entry"],
        "tone": "calm",
    }
    assert canonical["actors"]["guide"]["kind"].endswith(".Actor")
    assert canonical["locations"]["gate"]["kind"].endswith(".Location")
    assert canonical["scenes"]["intro"]["kind"].endswith(".Scene")
    assert canonical["scenes"]["intro"]["blocks"]["open"]["kind"].endswith(".Block")
    assert set(canonical["scenes"]["intro"]["templates"]) == {"local_note"}
    assert canonical["scenes"]["intro"]["blocks"]["open"]["actions"] == [
        {
            "successor_is_absolute": False,
            "successor_is_inferred": True,
            "successor_ref": "intro.close",
            "text": "Continue",
        }
    ]
    json.dumps(canonical)


def test_decompile_recompiles_importable_domain_block_kind() -> None:
    compiler = StoryCompiler()
    source = {
        "label": "domain_kind",
        "scenes": {
            "intro": {
                "blocks": {
                    "custom": {"kind": DomainBlock, "content": "Custom"},
                }
            }
        },
    }

    canonical = compiler.decompile(compiler.compile(source))
    restored = compiler.compile(canonical)
    custom = restored.template_registry.find_one(Selector(has_identifier="intro.custom"))

    assert canonical["scenes"]["intro"]["blocks"]["custom"]["kind"] == (
        f"{DomainBlock.__module__}.{DomainBlock.__qualname__}"
    )
    assert custom is not None
    assert isinstance(custom.payload, DomainBlock)


def test_decompile_makes_inferred_and_multiple_entries_explicit() -> None:
    compiler = StoryCompiler()
    inferred = compiler.decompile(
        compiler.compile(
            {
                "label": "inferred_entry",
                "scenes": {"intro": {"blocks": {"start": {"content": "Start"}}}},
            }
        )
    )
    multiple = compiler.decompile(
        compiler.compile(
            {
                "label": "multiple_entries",
                "metadata": {"start_at": ["intro.first", "intro.second"]},
                "scenes": {
                    "intro": {
                        "blocks": {
                            "first": {"content": "First"},
                            "second": {"content": "Second"},
                        }
                    }
                },
            }
        )
    )

    assert inferred["metadata"]["start_at"] == "intro.start"
    assert multiple["metadata"]["start_at"] == ["intro.first", "intro.second"]


def test_reference_world_decompiles_to_stable_cardinal_data() -> None:
    source = yaml.safe_load(Path("worlds/reference/script.yaml").read_text(encoding="utf-8"))

    canonical, recanonical = _decompile_twice(source)

    assert canonical == recanonical
    assert set(canonical["scenes"]) == {"prologue", "chapter1", "epilogue"}
    assert set(canonical["scenes"]["prologue"]["blocks"]) == {
        "start",
        "meet_aria",
        "request_help",
        "innkeeper",
        "rumors",
    }
