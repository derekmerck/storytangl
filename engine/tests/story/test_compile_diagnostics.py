"""Compiler diagnostics contract tests for story fabula bundles.

Organized by behavior:
- Bundle contract: valid scripts expose no compile issues.
- Structural refs: missing successor, actor, and location refs become issues.
- Source integrity: duplicate normalized labels are recorded without raising.
- Entry resolution: invalid or empty entry selection is recorded at compile time.
- Payload construction: a payload that will not build is downgraded loudly.
- Unknown keys: authored keys a payload kind cannot carry are reported.
- Aggregation: one compile can emit multiple deterministic issues.
"""

from __future__ import annotations

import logging
from typing import Any

from pydantic import Field

from tangl.core import Selector
from tangl.story.episode import Block, Scene
from tangl.story.fabula import CompileSeverity, StoryCompiler
from tangl.vm import TraversableNode


class NarratedScene(Scene):
    """Domain scene kind that declares its own ``text`` field."""

    text: str = Field(default="")


# ============================================================================
# Helpers
# ============================================================================


def _valid_script() -> dict[str, Any]:
    return {
        "label": "compile_diag",
        "metadata": {"start_at": "intro.start"},
        "actors": {
            "guide": {"name": "Guide"},
        },
        "locations": {
            "square": {"name": "Square"},
        },
        "scenes": {
            "intro": {
                "blocks": {
                    "start": {"content": "Start"},
                }
            }
        },
    }


def _compile(script: dict[str, Any]):
    return StoryCompiler().compile(script)


# ============================================================================
# Bundle Contract
# ============================================================================


class TestCompileDiagnosticsBundleContract:
    """Tests for the compile diagnostics surface on StoryTemplateBundle."""

    def test_valid_script_returns_no_compile_issues(self) -> None:
        bundle = _compile(_valid_script())

        assert bundle.issues == []

    def test_multi_file_source_map_does_not_reuse_first_file_as_default(self) -> None:
        script = _valid_script()
        script["scenes"]["intro"]["blocks"]["start"]["roles"] = [
            {"label": "host", "actor_ref": "missing_actor"},
        ]

        bundle = StoryCompiler().compile(
            script,
            source_map={
                "__source_files__": [
                    {"path": "scripts/a.yaml", "story_key": None},
                    {"path": "scripts/b.yaml", "story_key": None},
                ]
            },
        )

        issue = bundle.issues[0]
        assert issue.source_ref is not None
        assert issue.source_ref.path is None
        assert issue.source_ref.story_key is None
        assert issue.source_ref.authored_path == "scenes[0].intro.blocks[0].start.roles[0]"


# ============================================================================
# Structural Reference Issues
# ============================================================================


class TestCompileDiagnosticsStructuralRefs:
    """Tests for bundle-local dangling reference diagnostics."""

    def test_dangling_successor_is_recorded_on_bundle(self) -> None:
        script = _valid_script()
        script["scenes"]["intro"]["blocks"]["start"]["actions"] = [
            {"text": "Go", "successor": "missing"},
        ]

        bundle = _compile(script)

        assert len(bundle.issues) == 1
        issue = bundle.issues[0]
        assert issue.code == "compile:dangling_successor_ref"
        assert issue.severity is CompileSeverity.ERROR
        assert issue.phase == "compile"
        assert issue.subject_label == "intro.start.actions[0]"
        assert issue.related_identifiers == ["intro.missing"]
        assert issue.details == {
            "field": "actions",
            "authored_ref": "missing",
            "canonical_ref": "intro.missing",
        }
        assert issue.source_ref is not None
        assert issue.source_ref.authored_path == "scenes[0].intro.blocks[0].start.actions[0]"

    def test_dangling_actor_ref_is_recorded_on_bundle(self) -> None:
        script = _valid_script()
        script["scenes"]["intro"]["blocks"]["start"]["roles"] = [
            {"label": "host", "actor_ref": "missing_actor"},
        ]

        bundle = _compile(script)

        assert len(bundle.issues) == 1
        issue = bundle.issues[0]
        assert issue.code == "compile:dangling_actor_ref"
        assert issue.subject_label == "intro.start.host"
        assert issue.related_identifiers == ["missing_actor"]
        assert issue.details == {
            "reference_key": "actor_ref",
            "missing_ref": "missing_actor",
        }
        assert issue.source_ref is not None
        assert issue.source_ref.authored_path == "scenes[0].intro.blocks[0].start.roles[0]"

    def test_dangling_location_ref_is_recorded_on_bundle(self) -> None:
        script = _valid_script()
        script["scenes"]["intro"]["blocks"]["start"]["settings"] = [
            {"label": "where", "location_ref": "missing_place"},
        ]

        bundle = _compile(script)

        assert len(bundle.issues) == 1
        issue = bundle.issues[0]
        assert issue.code == "compile:dangling_location_ref"
        assert issue.subject_label == "intro.start.where"
        assert issue.related_identifiers == ["missing_place"]
        assert issue.details == {
            "reference_key": "location_ref",
            "missing_ref": "missing_place",
        }
        assert issue.source_ref is not None
        assert issue.source_ref.authored_path == "scenes[0].intro.blocks[0].start.settings[0]"


# ============================================================================
# Source Integrity And Entry Resolution
# ============================================================================


class TestCompileDiagnosticsSourceIntegrity:
    """Tests for duplicate labels and entry resolution diagnostics."""

    def test_duplicate_normalized_labels_are_recorded_without_raising(self) -> None:
        script = _valid_script()
        script["templates"] = {
            "guide": {"kind": "Actor", "name": "Template Guide"},
        }

        bundle = _compile(script)

        assert len(bundle.issues) == 1
        issue = bundle.issues[0]
        assert issue.code == "compile:duplicate_label"
        assert issue.subject_label == "guide"
        assert issue.related_identifiers == []
        assert issue.details == {
            "normalized_label": "guide",
            "occurrences": ["templates[0].guide", "actors[0].guide"],
        }

    def test_duplicate_list_items_keep_distinct_occurrence_paths(self) -> None:
        script = {
            "label": "duplicate_scenes",
            "metadata": {"start_at": "scene1.block1"},
            "scenes": [
                {"label": "scene1", "blocks": {"block1": {"content": "A"}}},
                {"label": "scene1", "blocks": {"block2": {"content": "B"}}},
            ],
        }

        bundle = _compile(script)

        issue = next(issue for issue in bundle.issues if issue.code == "compile:duplicate_label")
        assert issue.details == {
            "normalized_label": "scene1",
            "occurrences": ["scenes[0].scene1", "scenes[1].scene1"],
        }

    def test_invalid_start_at_records_empty_entry_resolution(self) -> None:
        script = _valid_script()
        script["metadata"]["start_at"] = "missing_entry"

        bundle = _compile(script)

        assert bundle.entry_template_ids == ["missing_entry"]
        assert len(bundle.issues) == 1
        issue = bundle.issues[0]
        assert issue.code == "compile:empty_entry_resolution"
        assert issue.subject_label == "compile_diag"
        assert issue.details == {
            "requested_entry_ids": ["missing_entry"],
            "resolution_strategy": "metadata.start_at",
        }
        assert issue.source_ref is not None
        assert issue.source_ref.authored_path == "metadata.start_at"


# ============================================================================
# Payload Construction
# ============================================================================


class TestCompileDiagnosticsPayloadConstruction:
    """Tests for the diagnostic emitted when an authored payload will not build.

    ``conditions:`` is the authored gating surface (``BaseScriptItem`` in the
    IR schema declares it; nothing declares ``availability:``). Authoring bare
    strings under the runtime ``availability`` field therefore fails
    validation, and the compiler downgrades that block to a plain
    ``TraversableNode``. These tests pin that the downgrade is reported.
    """

    @staticmethod
    def _payload(bundle, label: str):
        templ = bundle.template_registry.find_one(Selector(label=label))
        assert templ is not None
        return templ.payload

    def test_authored_conditions_compile_into_availability_predicates(self) -> None:
        script = _valid_script()
        script["scenes"]["intro"]["blocks"]["start"]["conditions"] = ["flag"]

        bundle = _compile(script)

        assert bundle.issues == []
        payload = self._payload(bundle, "intro.start")
        assert isinstance(payload, Block)
        assert [predicate.expr for predicate in payload.availability] == ["flag"]

    def test_availability_string_list_records_construction_failure(self) -> None:
        script = _valid_script()
        script["scenes"]["intro"]["blocks"]["start"]["availability"] = ["flag"]

        bundle = _compile(script)

        assert len(bundle.issues) == 1
        issue = bundle.issues[0]
        assert issue.code == "compile:payload_construction_failed"
        assert issue.severity is CompileSeverity.ERROR
        assert issue.phase == "compile"
        assert issue.subject_label == "start"
        assert issue.details["kind"] == "Block"
        assert issue.details["fallback_kind"] == "TraversableNode"
        assert "conditions:" in issue.details["hint"]
        assert "Predicate" in issue.details["error"]
        assert issue.source_ref is not None
        assert issue.source_ref.authored_path == "scenes[0].intro.blocks[0].start"

    def test_construction_failure_is_logged_with_block_and_kind(
        self,
        caplog,
    ) -> None:
        script = _valid_script()
        script["scenes"]["intro"]["blocks"]["start"]["availability"] = ["flag"]

        with caplog.at_level(logging.WARNING, logger="tangl.story.fabula.compiler"):
            _compile(script)

        assert len(caplog.records) == 1
        message = caplog.records[0].getMessage()
        assert "'start'" in message
        assert "Block" in message
        assert "scenes[0].intro.blocks[0].start" in message

    def test_degraded_payload_keeps_its_own_reference_diagnostics(self) -> None:
        script = _valid_script()
        script["scenes"]["intro"]["blocks"]["start"]["availability"] = ["flag"]
        script["scenes"]["intro"]["blocks"]["start"]["roles"] = [
            {"label": "host", "actor_ref": "missing_actor"},
        ]
        script["scenes"]["intro"]["blocks"]["other"] = {
            "content": "Other",
            "actions": [{"text": "Go", "successor": "missing"}],
        }

        bundle = _compile(script)

        payload = self._payload(bundle, "intro.start")
        assert type(payload) is TraversableNode
        # Reference diagnostics read the authored specs, so a payload that
        # failed to construct still reports everything the compiler knows.
        assert [issue.code for issue in bundle.issues] == [
            "compile:payload_construction_failed",
            "compile:dangling_actor_ref",
            "compile:dangling_successor_ref",
        ]
        assert [
            issue.source_ref.authored_path
            for issue in bundle.issues
            if issue.source_ref is not None
        ] == [
            "scenes[0].intro.blocks[0].start",
            "scenes[0].intro.blocks[0].start.roles[0]",
            "scenes[0].intro.blocks[1].other.actions[0]",
        ]

    def test_scene_payload_construction_failure_is_recorded(self) -> None:
        script = _valid_script()
        script["scenes"]["intro"]["availability"] = ["flag"]

        bundle = _compile(script)

        assert len(bundle.issues) == 1
        issue = bundle.issues[0]
        assert issue.code == "compile:payload_construction_failed"
        assert issue.subject_label == "intro"
        assert issue.details["kind"] == "Scene"
        assert issue.source_ref is not None
        assert issue.source_ref.authored_path == "scenes[0].intro"


# ============================================================================
# Unknown Authored Keys
# ============================================================================


class TestCompileDiagnosticsUnknownAuthoredKeys:
    """Tests for authored keys discarded because the payload kind lacks them.

    The compiler filters authored data down to the payload kind's own fields.
    Keys it folds elsewhere first (``conditions`` into ``availability``, action
    successor spellings, scene ``text``) must stay silent; what is left is
    authored intent that goes nowhere, and is reported as a warning.
    """

    @staticmethod
    def _unknown_key_issues(bundle):
        return [
            issue
            for issue in bundle.issues
            if issue.code == "compile:unknown_authored_key"
        ]

    def test_location_conditions_are_reported_as_discarded(self) -> None:
        script = _valid_script()
        script["locations"]["square"]["conditions"] = ["flag"]

        bundle = _compile(script)

        assert len(bundle.issues) == 1
        issue = bundle.issues[0]
        assert issue.code == "compile:unknown_authored_key"
        assert issue.severity is CompileSeverity.WARNING
        assert issue.phase == "compile"
        assert issue.subject_label == "square"
        assert issue.details["key"] == "conditions"
        assert issue.details["kind"] == "Location"
        assert "not a traversable node" in issue.details["hint"]
        assert issue.source_ref is not None
        assert issue.source_ref.authored_path == "locations[0].square.conditions"

    def test_misspelled_key_suggests_the_near_field_name(self) -> None:
        script = _valid_script()
        script["scenes"]["intro"]["blocks"]["start"]["contents"] = "Start"

        issues = self._unknown_key_issues(_compile(script))

        assert len(issues) == 1
        assert issues[0].details["key"] == "contents"
        assert issues[0].details["hint"] == "Did you mean 'content'?"

    def test_authored_data_lost_to_a_non_block_kind_is_reported(self) -> None:
        script = _valid_script()
        script["scenes"]["intro"]["blocks"]["start"]["kind"] = "Node"
        script["scenes"]["intro"]["blocks"]["start"]["actions"] = [
            {"text": "Go", "successor": "intro.start"},
        ]

        issues = self._unknown_key_issues(_compile(script))

        assert [issue.details["key"] for issue in issues] == ["actions", "content"]
        assert {issue.details["kind"] for issue in issues} == {"TraversableNode"}

    def test_normalized_containers_the_author_left_empty_are_not_reported(self) -> None:
        script = _valid_script()
        script["scenes"]["intro"]["blocks"]["start"] = {"kind": "Node"}

        assert self._unknown_key_issues(_compile(script)) == []

    def test_compiler_handled_keys_are_not_reported(self) -> None:
        script = _valid_script()
        script["scenes"]["intro"]["kind"] = "Scene"
        script["scenes"]["intro"]["text"] = "Intro"
        script["scenes"]["intro"]["templates"] = {
            "note": {"kind": "Actor", "name": "Note"},
        }
        script["actors"]["guide"]["locked"] = False
        script["actors"]["guide"]["ancestor_tags"] = []

        assert self._unknown_key_issues(_compile(script)) == []

    def test_scene_text_is_kept_by_a_kind_that_declares_it(self) -> None:
        script = _valid_script()
        script["scenes"]["intro"]["kind"] = NarratedScene
        script["scenes"]["intro"]["text"] = "Narration"

        bundle = _compile(script)

        assert self._unknown_key_issues(bundle) == []
        templ = bundle.template_registry.find_one(Selector(label="intro"))
        assert templ is not None
        assert isinstance(templ.payload, NarratedScene)
        assert templ.payload.text == "Narration"
        assert templ.payload.title == "Narration"

    def test_synthetic_scene_title_is_not_reported_as_authored(self) -> None:
        script = _valid_script()
        script["scenes"]["intro"]["kind"] = "Node"
        script["scenes"]["intro"]["text"] = "Narration"

        issues = self._unknown_key_issues(_compile(script))

        # ``title`` is compiler-synthesized, so only the authored ``text`` the
        # resolved kind cannot carry is reported.
        assert [issue.details["key"] for issue in issues] == ["text"]

    def test_action_successor_spellings_are_not_reported(self) -> None:
        script = _valid_script()
        script["templates"] = {
            "go": {"kind": "Action", "text": "Go", "target_node": "intro.start"},
        }

        assert self._unknown_key_issues(_compile(script)) == []

    def test_validated_ir_roundtrip_reports_no_unknown_keys(self) -> None:
        script = _valid_script()
        script["metadata"].update({"title": "Compile Diag", "author": "Tests"})
        validated = StoryCompiler.validate_ir(script)

        bundle = StoryCompiler().compile(validated)

        assert self._unknown_key_issues(bundle) == []


# ============================================================================
# Aggregation And Ordering
# ============================================================================


class TestCompileDiagnosticsAggregation:
    """Tests for multi-issue collection and deterministic ordering."""

    def test_compile_collects_multiple_issues_in_deterministic_order(self) -> None:
        script = _valid_script()
        script["templates"] = {
            "guide": {"kind": "Actor", "name": "Template Guide"},
        }
        script["scenes"]["intro"]["blocks"]["start"]["actions"] = [
            {"text": "Go", "successor": "missing"},
        ]
        script["scenes"]["intro"]["blocks"]["start"]["roles"] = [
            {"label": "host", "actor_ref": "missing_actor"},
        ]
        script["scenes"]["intro"]["blocks"]["start"]["settings"] = [
            {"label": "where", "location_ref": "missing_place"},
        ]

        bundle = _compile(script)

        assert [issue.code for issue in bundle.issues] == [
            "compile:dangling_successor_ref",
            "compile:dangling_actor_ref",
            "compile:dangling_location_ref",
            "compile:duplicate_label",
        ]
        assert [issue.source_ref.authored_path if issue.source_ref is not None else None for issue in bundle.issues] == [
            "scenes[0].intro.blocks[0].start.actions[0]",
            "scenes[0].intro.blocks[0].start.roles[0]",
            "scenes[0].intro.blocks[0].start.settings[0]",
            "templates[0].guide",
        ]
