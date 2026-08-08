"""Typer-based CLI for the StoryTangl developer topic reference index."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer
import yaml
from pydantic import BaseModel

from .builder import DEFAULT_DB_PATH, REPO_ROOT, build_index
from .issues import issue_cache_path, load_issue_cache, sync_issues
from .query import build_context_pack, get_topic_map, search_topics
from .storage import DevRefDatabase


app = typer.Typer(
    help="Developer topic reference utilities for StoryTangl source, docs, tests, and demos.",
    no_args_is_help=True,
)


DbOption = Annotated[
    Path | None,
    typer.Option(help="SQLite database path. Defaults to tmp/devref/devref.sqlite3."),
]
FacetOption = Annotated[
    list[str] | None,
    typer.Option("--facet", help="Optional facet filter. May be repeated."),
]
LimitOption = Annotated[
    int,
    typer.Option(help="Maximum number of results to return."),
]
FormatOption = Annotated[
    str,
    typer.Option("--format", help="Output format: yaml or json."),
]


def _render(value: BaseModel | dict[str, object], *, output_format: str) -> None:
    payload = value.model_dump(mode="python") if isinstance(value, BaseModel) else value
    if output_format == "json":
        typer.echo(json.dumps(payload, indent=2, sort_keys=False))
        return
    typer.echo(yaml.dump(payload, indent=2, sort_keys=False))


@app.command("build")
def build_command(
    db: DbOption = None,
    full: bool = typer.Option(False, "--full", help="Force a full rebuild instead of incremental refresh."),
    output_format: FormatOption = "yaml",
) -> None:
    """Build or refresh the local dev topic index."""

    report = build_index(db_path=db or DEFAULT_DB_PATH, incremental=not full)
    _render(report, output_format=output_format)


@app.command("sync-issues")
def sync_issues_command(
    limit: int = typer.Option(500, help="Maximum number of issues to request from GitHub."),
    state: str = typer.Option(
        "open",
        help="Issue state to fetch: open, closed, or all. Retrieval does not show "
        "state, so indexing closed issues presents finished work as outstanding.",
    ),
    output_format: FormatOption = "yaml",
) -> None:
    """Refresh the offline snapshot of open ``devref:``-labelled issues.

    This is the only devref command that reaches the network. It writes
    ``tmp/devref/issues.json``; ``build`` reads whatever snapshot is on disk,
    so the build itself stays offline and deterministic.
    """

    try:
        report = sync_issues(REPO_ROOT, limit=limit, state=state)
    except (OSError, RuntimeError) as exc:
        typer.secho(f"Could not sync issues: {exc}", err=True, fg=typer.colors.RED)
        raise typer.Exit(1) from exc
    _render(report, output_format=output_format)


@app.command("find")
def find_command(
    query: str = typer.Argument(..., help="Free-text topic query."),
    facets: FacetOption = None,
    limit: LimitOption = 20,
    db: DbOption = None,
    output_format: FormatOption = "yaml",
) -> None:
    """Search topics and ranked artifacts."""

    response = search_topics(query, facets=facets, limit=limit, db_path=db or DEFAULT_DB_PATH)
    _render(response, output_format=output_format)


@app.command("map")
def map_command(
    topic_id: str = typer.Argument(..., help="Developer topic id."),
    limit: LimitOption = 24,
    db: DbOption = None,
    output_format: FormatOption = "yaml",
) -> None:
    """Show one topic with related topics and linked artifacts."""

    topic_map = get_topic_map(topic_id, limit=limit, db_path=db or DEFAULT_DB_PATH)
    _render(topic_map, output_format=output_format)


@app.command("pack")
def pack_command(
    topic_ids: list[str] = typer.Argument(..., help="One or more developer topic ids."),
    facets: FacetOption = None,
    limit: LimitOption = 12,
    db: DbOption = None,
    output_format: FormatOption = "yaml",
) -> None:
    """Build a compact agent-oriented context pack."""

    pack = build_context_pack(topic_ids, facets=facets, limit=limit, db_path=db or DEFAULT_DB_PATH)
    _render(pack, output_format=output_format)


@app.command("status")
def status_command(
    db: DbOption = None,
    output_format: FormatOption = "yaml",
) -> None:
    """Report database freshness and indexed-object counts."""

    database = DevRefDatabase(db or DEFAULT_DB_PATH)
    exists = database.path.exists()
    has_schema = database.has_schema()
    built = database.is_built()
    meta = database.get_meta() if built else {}
    state = "missing"
    if exists and not has_schema:
        state = "uninitialized"
    elif has_schema and not built:
        state = "schema_only"
    elif built:
        state = "built"
    cache_path = issue_cache_path(REPO_ROOT)
    issue_cache = load_issue_cache(cache_path) if cache_path.exists() else None
    payload = {
        "db_path": str(database.path),
        "exists": exists,
        "has_schema": has_schema,
        "built": built,
        "state": state,
        "built_at": meta.get("built_at"),
        "builder_version": meta.get("builder_version"),
        "used_fts": meta.get("used_fts") == "1" if built else False,
        "artifacts": database.artifact_count() if has_schema else 0,
        "symbols": database.symbol_count() if has_schema else 0,
        "topic_links": database.topic_link_count() if has_schema else 0,
        "artifact_links": database.artifact_link_count() if has_schema else 0,
        "issue_cache_path": str(cache_path),
        "issue_cache_synced_at": issue_cache.generated_at.isoformat() if issue_cache else None,
        "issues_cached": len(issue_cache.issues) if issue_cache else 0,
        "issues_indexed": database.artifact_kind_count("issue") if has_schema else 0,
    }
    _render(payload, output_format=output_format)


def run() -> None:
    """Run the Typer application."""

    app()


if __name__ == "__main__":
    run()
