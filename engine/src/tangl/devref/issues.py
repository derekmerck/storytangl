"""GitHub issue snapshot used as a devref build source.

Why
---
Issues are the third surface of the issues <-> design-docs <-> code triangle,
but a build that reaches the network is neither offline, deterministic, nor
disposable. Issues therefore reach the index through an on-disk snapshot:
:func:`sync_issues` shells out to the GitHub CLI and writes the snapshot,
and the builder reads whatever is on disk, indexing nothing when absent.

Key Features
------------
- The ``devref:<topic>`` label is the convention. Each such label names a
  topic from the same curated vocabulary that docs and code annotate with
  ``storytangl-topic``, so both sides join on one registry.
- Umbrella issues, marked with ``kind:milestone``, ``govern`` their topics.
  Ordinary issues merely ``mention`` them.

Notes
-----
GitHub search cannot match a label prefix, so the snapshot is filtered
locally: fetch the issue list once, then keep the records that carry at
least one ``devref:`` label.

See also
--------
:mod:`tangl.devref.builder` : turns the snapshot into ``issue`` artifacts.
"""

from __future__ import annotations

from datetime import UTC, datetime
import json
import logging
from pathlib import Path
import subprocess
from typing import Any

from .models import IssueCache, IssueRecord, IssueSyncReport
from .topics import load_topics


logger = logging.getLogger(__name__)

ISSUE_CACHE_RELPATH = "tmp/devref/issues.json"
TOPIC_LABEL_PREFIX = "devref:"
GOVERNING_LABELS = frozenset({"kind:milestone"})
GH_JSON_FIELDS = "number,title,body,labels,state,url"


def issue_cache_path(repo_root: Path) -> Path:
    """Return the issue snapshot path for one checkout."""

    return repo_root / ISSUE_CACHE_RELPATH


def topic_labels(labels: list[str]) -> list[str]:
    """Return the topic ids named by an issue's ``devref:<topic>`` labels."""

    return sorted(
        {
            label[len(TOPIC_LABEL_PREFIX):]
            for label in labels
            if label.startswith(TOPIC_LABEL_PREFIX) and label != TOPIC_LABEL_PREFIX
        }
    )


def is_governing(labels: list[str]) -> bool:
    """Return whether an issue is an umbrella that governs its topics."""

    return any(label in GOVERNING_LABELS for label in labels)


def load_issue_cache(path: Path) -> IssueCache:
    """Load one issue snapshot from disk."""

    return IssueCache.model_validate_json(path.read_text(encoding="utf-8"))


def _to_record(payload: dict[str, Any]) -> IssueRecord:
    """Narrow one raw ``gh issue list`` record to the fields devref indexes."""

    return IssueRecord(
        number=int(payload["number"]),
        title=str(payload["title"]),
        body=str(payload.get("body") or ""),
        state=str(payload.get("state") or ""),
        url=str(payload.get("url") or ""),
        labels=sorted(str(label["name"]) for label in payload.get("labels") or []),
    )


def fetch_issues(repo_root: Path, *, limit: int, state: str) -> list[dict[str, Any]]:
    """Fetch raw issue records from the GitHub CLI.

    The command runs inside ``repo_root`` so ``gh`` resolves the repository from
    that checkout's own remote.
    """

    command = [
        "gh",
        "issue",
        "list",
        "--state",
        state,
        "--limit",
        str(limit),
        "--json",
        GH_JSON_FIELDS,
    ]
    logger.debug("Fetching issues with the GitHub CLI: %s", " ".join(command))
    result = subprocess.run(
        command,
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"gh issue list failed with exit code {result.returncode}: {result.stderr.strip()}"
        )
    return json.loads(result.stdout)


def sync_issues(repo_root: Path, *, limit: int = 500, state: str = "open") -> IssueSyncReport:
    """Refresh the offline issue snapshot that the builder indexes.

    Only open issues are captured by default. Retrieval surfaces an issue's
    title and topics but not its state, so indexing closed work would present
    finished business as outstanding. Pass ``state="all"`` for archaeology.
    """

    payload = fetch_issues(repo_root, limit=limit, state=state)
    records = [
        record
        for record in (_to_record(item) for item in payload)
        if topic_labels(record.labels)
    ]
    records.sort(key=lambda record: record.number)

    target = issue_cache_path(repo_root)
    target.parent.mkdir(parents=True, exist_ok=True)
    cache = IssueCache(generated_at=datetime.now(UTC), issues=records)
    # Write through a sibling and rename, so an interrupted sync leaves the
    # previous snapshot intact rather than truncated JSON the builder cannot read.
    staged = target.with_suffix(".json.tmp")
    staged.write_text(cache.model_dump_json(indent=2) + "\n", encoding="utf-8")
    staged.replace(target)

    truncated = len(payload) >= limit
    if truncated:
        logger.warning(
            "GitHub returned the full requested page of %d issues; the snapshot may be "
            "incomplete. Re-run with a higher --limit.",
            limit,
        )
    known_topic_ids = {topic.topic_id for topic in load_topics()}
    seen = sorted({topic_id for record in records for topic_id in topic_labels(record.labels)})
    unknown = [topic_id for topic_id in seen if topic_id not in known_topic_ids]
    if unknown:
        logger.warning(
            "Ignoring devref labels that name no registered topic: %s",
            ", ".join(unknown),
        )
    logger.info("Wrote %d issues to the devref issue snapshot at %s", len(records), target)
    return IssueSyncReport(
        cache_path=str(target),
        fetched=len(payload),
        indexed=len(records),
        truncated=truncated,
        topics=[topic_id for topic_id in seen if topic_id in known_topic_ids],
        unknown_topics=unknown,
    )
