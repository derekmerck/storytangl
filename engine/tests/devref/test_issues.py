"""GitHub issue snapshot ingestion.

Every test here writes its own snapshot fixture: the build must stay offline,
so nothing in this module is allowed to reach the network.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from tangl.devref import issues as issues_module
from tangl.devref.builder import build_index
from tangl.devref.issues import ISSUE_CACHE_RELPATH, sync_issues
from tangl.devref.query import build_context_pack, search_topics
from tangl.devref.storage import DevRefDatabase


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _issue(
    number: int,
    title: str,
    labels: list[str],
    *,
    body: str = "",
    state: str = "OPEN",
) -> dict[str, Any]:
    return {
        "number": number,
        "title": title,
        "body": body,
        "state": state,
        "url": f"https://github.com/derekmerck/storytangl/issues/{number}",
        "labels": labels,
    }


def _repo(tmp_path: Path, issues: list[dict[str, Any]] | None = None) -> Path:
    """Build a miniature checkout with one design doc and an optional snapshot."""

    repo = tmp_path / "mini_repo"
    _write(
        repo / "docs" / "src" / "design" / "entity_model.md",
        "# Entity Model\n\nHow the entity primitive is layered.\n",
    )
    if issues is not None:
        _write(
            repo / ISSUE_CACHE_RELPATH,
            json.dumps({"generated_at": "2026-08-06T00:00:00Z", "issues": issues}),
        )
    return repo


def _issue_hits(topic: str, db_path: Path) -> list:
    return [
        artifact
        for artifact in search_topics(topic, db_path=db_path).artifacts
        if artifact.kind == "issue"
    ]


def test_labelled_issue_is_indexed_alongside_docs(tmp_path) -> None:
    """A ``devref:<topic>`` label joins an issue to the same topic as the docs."""

    # The wording deliberately avoids topic aliases, so the only thing that can
    # link this issue to ``entity`` is its label.
    repo_root = _repo(
        tmp_path,
        [
            _issue(
                101,
                "Stale pointer handed back after teardown",
                ["kind:bug", "devref:entity"],
                body="The lookup table returns a freed object.\n\nMore detail follows.",
            )
        ],
    )
    db_path = tmp_path / "mini.sqlite3"

    build_index(repo_root=repo_root, db_path=db_path, incremental=False)
    hits = _issue_hits("entity", db_path)
    kinds = {artifact.kind for artifact in search_topics("entity", db_path=db_path).artifacts}

    assert len(hits) == 1
    assert hits[0].title == "#101 Stale pointer handed back after teardown"
    assert hits[0].relation == "mentions"
    assert hits[0].facet == "notes"
    assert hits[0].topic_ids == ["entity"]
    assert hits[0].evidence_sources == ["manual_annotation"]
    # The issue is addressable on GitHub, not at a path inside the checkout.
    assert hits[0].source_path == "https://github.com/derekmerck/storytangl/issues/101"
    assert hits[0].summary == "The lookup table returns a freed object."
    # The point of the feature: issues arrive next to the docs, not instead.
    assert {"doc_section", "issue"} <= kinds


def test_milestone_issue_governs_its_topics(tmp_path) -> None:
    """``kind:milestone`` is the cheap umbrella signal, so the issue governs."""

    repo_root = _repo(
        tmp_path,
        [_issue(102, "Identity rework roadmap", ["kind:milestone", "devref:entity"])],
    )
    db_path = tmp_path / "mini.sqlite3"

    build_index(repo_root=repo_root, db_path=db_path, incremental=False)
    hits = _issue_hits("entity", db_path)

    assert len(hits) == 1
    assert hits[0].relation == "governs"
    assert hits[0].facet == "governance"
    # An empty body still needs a usable summary, so the title stands in.
    assert hits[0].summary == "Identity rework roadmap"


def test_issue_reaches_the_context_pack(tmp_path) -> None:
    """``pack`` is the agent surface, so issues have to land in it too."""

    repo_root = _repo(
        tmp_path,
        [_issue(103, "Ownership handoff is ambiguous", ["devref:entity"])],
    )
    db_path = tmp_path / "mini.sqlite3"

    build_index(repo_root=repo_root, db_path=db_path, incremental=False)
    pack = build_context_pack(["entity"], db_path=db_path)
    titles = [item.title for item in pack.items]

    assert "#103 Ownership handoff is ambiguous" in titles
    # Design docs outrank issues, so the governing doc still leads the bundle.
    assert titles.index("Entity Model") < titles.index("#103 Ownership handoff is ambiguous")


def test_unlabelled_and_unknown_topic_issues_are_not_linked(tmp_path) -> None:
    """Only registered ``devref:`` topics create links; the rest are inert."""

    repo_root = _repo(
        tmp_path,
        [
            _issue(104, "Tidy up the changelog", ["kind:bug"]),
            _issue(105, "Revisit the release checklist", ["devref:not_a_real_topic"]),
        ],
    )
    db_path = tmp_path / "mini.sqlite3"

    build_index(repo_root=repo_root, db_path=db_path, incremental=False)
    db = DevRefDatabase(db_path)
    keys = {row["artifact_key"] for row in db.load_rows("SELECT artifact_key FROM artifacts")}

    # An issue with no devref label produces no artifact at all.
    assert "issue:104" not in keys
    # An unknown topic still yields an artifact, but its label links nothing.
    assert "issue:105" in keys
    assert not _issue_hits("entity", db_path)
    assert db.scalar(
        """
        SELECT COUNT(*) FROM artifact_topics
        JOIN artifacts USING (artifact_id)
        WHERE artifacts.kind = 'issue' AND artifact_topics.evidence_source = 'manual_annotation'
        """
    ) == 0


def test_build_without_a_snapshot_indexes_no_issues(tmp_path) -> None:
    """Absent snapshot means the existing build behaviour is untouched."""

    repo_root = _repo(tmp_path)
    db_path = tmp_path / "mini.sqlite3"

    report = build_index(repo_root=repo_root, db_path=db_path, incremental=False)

    assert report.artifacts > 0
    assert DevRefDatabase(db_path).artifact_kind_count("issue") == 0


def test_incremental_build_tracks_snapshot_refresh_and_removal(tmp_path) -> None:
    """Refreshing or dropping the snapshot must not strand stale issues."""

    repo_root = _repo(
        tmp_path,
        [
            _issue(106, "Alpha follow-up", ["devref:entity"]),
            _issue(107, "Beta follow-up", ["devref:entity"]),
        ],
    )
    db_path = tmp_path / "mini.sqlite3"
    cache_path = repo_root / ISSUE_CACHE_RELPATH
    db = DevRefDatabase(db_path)

    build_index(repo_root=repo_root, db_path=db_path, incremental=False)
    assert db.artifact_kind_count("issue") == 2

    # A refresh that closes out one issue drops it from the index.
    _write(
        cache_path,
        json.dumps(
            {
                "generated_at": "2026-08-07T00:00:00Z",
                "issues": [_issue(106, "Alpha follow-up, revised", ["devref:entity"])],
            }
        ),
    )
    refreshed = build_index(repo_root=repo_root, db_path=db_path, incremental=True)

    assert refreshed.build_mode == "incremental"
    assert db.artifact_kind_count("issue") == 1
    assert _issue_hits("entity", db_path)[0].title == "#106 Alpha follow-up, revised"

    # Deleting the snapshot clears the issues but leaves the rest of the index.
    cache_path.unlink()
    dropped = build_index(repo_root=repo_root, db_path=db_path, incremental=True)

    assert dropped.build_mode == "incremental"
    assert db.artifact_kind_count("issue") == 0
    assert db.artifact_count() > 0


def test_sync_issues_writes_a_snapshot_the_builder_can_read(tmp_path, monkeypatch) -> None:
    """``sync-issues`` is the only networked step, so its output is the contract."""

    repo_root = _repo(tmp_path)
    db_path = tmp_path / "mini.sqlite3"
    captured: dict[str, Any] = {}

    def fake_fetch(root: Path, *, limit: int, state: str):
        captured.update(root=root, limit=limit, state=state)
        return [
            {
                "number": 108,
                "title": "Ownership is unclear",
                "body": "Who owns the freed handle?",
                "state": "OPEN",
                "url": "https://github.com/derekmerck/storytangl/issues/108",
                "labels": [{"name": "devref:entity"}, {"name": "kind:feature"}],
            },
            {
                "number": 109,
                "title": "Unrelated chore",
                "body": "",
                "state": "CLOSED",
                "url": "https://github.com/derekmerck/storytangl/issues/109",
                "labels": [{"name": "kind:docs"}],
            },
            {
                "number": 110,
                "title": "Mystery topic",
                "body": "",
                "state": "OPEN",
                "url": "https://github.com/derekmerck/storytangl/issues/110",
                "labels": [{"name": "devref:not_a_real_topic"}],
            },
        ]

    monkeypatch.setattr(issues_module, "fetch_issues", fake_fetch)
    report = sync_issues(repo_root, limit=50, state="open")

    assert captured == {"root": repo_root, "limit": 50, "state": "open"}
    assert report.cache_path == str(repo_root / ISSUE_CACHE_RELPATH)
    assert report.fetched == 3
    # Only devref-labelled issues are cached, whether or not the topic resolves.
    assert report.indexed == 2
    assert report.topics == ["entity"]
    assert report.unknown_topics == ["not_a_real_topic"]

    build_index(repo_root=repo_root, db_path=db_path, incremental=False)
    hits = _issue_hits("entity", db_path)

    assert [artifact.title for artifact in hits] == ["#108 Ownership is unclear"]


def test_fetch_issues_reports_a_failing_gh_invocation(tmp_path, monkeypatch) -> None:
    """A missing or unauthenticated ``gh`` has to surface, not silently no-op."""

    class _Result:
        returncode = 1
        stdout = ""
        stderr = "gh: not authenticated\n"

    monkeypatch.setattr(issues_module.subprocess, "run", lambda *a, **k: _Result())

    with pytest.raises(RuntimeError, match="not authenticated"):
        issues_module.fetch_issues(tmp_path, limit=10, state="all")
