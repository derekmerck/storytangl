"""Compiler diagnostics contract tests for story fabula bundles.

Organized by behavior:
- Bundle contract: valid scripts expose no compile issues.
- Structural refs: missing successor, actor, and location refs become issues.
- Source integrity: duplicate normalized labels are recorded without raising.
- Entry resolution: invalid or empty entry selection is recorded at compile time.
- Aggregation: one compile can emit multiple deterministic issues.
"""

from __future__ import annotations

from typing import Any

from tangl.story.fabula import CompileSeverity, StoryCompiler


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
