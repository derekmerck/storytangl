from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .builder import DEFAULT_DB_PATH, FACET_PRIORITY, build_index, normalize_text
from .models import (
    ArtifactHit,
    ContextPack,
    ContextPackItem,
    DevTopicFacet,
    SearchResponse,
    TopicDefinition,
    TopicGraphLink,
    TopicHit,
    TopicMap,
)
from .storage import DevRefDatabase
from .topics import load_topics


def _ensure_db(db_path: str | Path | None) -> DevRefDatabase:
    db = DevRefDatabase(db_path or DEFAULT_DB_PATH)
    if not db.is_built():
        build_index(db_path=db.path)
    return db


def _parse_query(query: str, facets: list[DevTopicFacet] | None) -> tuple[list[str], list[DevTopicFacet]]:
    requested = list(facets or [])
    raw_terms = [part.strip().lower() for part in query.replace("+", " ").split() if part.strip()]
    inferred: list[DevTopicFacet] = []
    terms: list[str] = []
    for term in raw_terms:
        if term in FACET_PRIORITY and term not in inferred and term not in requested:
            inferred.append(term)  # type: ignore[arg-type]
        else:
            terms.append(term)
    return terms, requested or inferred


def _topic_matches(terms: list[str]) -> list[TopicHit]:
    topics = load_topics()
    hits: list[TopicHit] = []
    if not terms:
        return []
    normalized_terms = [normalize_text(term) for term in terms]
    for topic in topics:
        aliases = [topic.topic_id, topic.display_name, *topic.aliases]
        best_score = 0.0
        best_alias: str | None = None
        for alias in aliases:
            alias_norm = normalize_text(alias)
            if all(alias_norm == term for term in normalized_terms):
                best_score = max(best_score, 120.0)
                best_alias = alias
            elif all(term == normalize_text(topic.topic_id) for term in normalized_terms):
                best_score = max(best_score, 115.0)
                best_alias = topic.topic_id
            elif all(term in alias_norm for term in normalized_terms):
                best_score = max(best_score, 85.0)
                best_alias = alias
        if best_score > 0:
            hits.append(
                TopicHit(
                    topic_id=topic.topic_id,
                    display_name=topic.display_name,
                    layer=topic.layer,
                    short_description=topic.short_description,
                    score=best_score,
                    matched_alias=best_alias,
                )
            )
    return sorted(hits, key=lambda item: (-item.score, item.display_name))


def _fts_scores(db: DevRefDatabase, terms: list[str]) -> dict[int, float]:
    if not terms:
        return {}
    meta = db.get_meta()
    if meta.get("used_fts") != "1":
        return {}
    query = " ".join(terms)
    rows = db.load_rows(
        """
        SELECT artifact_id, bm25(artifact_fts) AS rank
        FROM artifact_fts
        WHERE artifact_fts MATCH ?
        ORDER BY rank
        LIMIT 200
        """,
        (query,),
    )
    return {row["artifact_id"]: max(0.0, 20.0 - float(row["rank"])) for row in rows}


def _all_artifact_hits(db: DevRefDatabase) -> dict[int, dict[str, Any]]:
    rows = db.load_rows(
        """
        SELECT
            artifacts.artifact_id,
            artifacts.title,
            artifacts.kind,
            artifacts.facet,
            artifacts.relation,
            artifacts.source_path,
            artifacts.line,
            artifacts.summary,
            artifacts.content,
            artifacts.qualified_name,
            artifact_topics.topic_id,
            artifact_topics.evidence_source,
            artifact_topics.weight
        FROM artifacts
        LEFT JOIN artifact_topics ON artifact_topics.artifact_id = artifacts.artifact_id
        ORDER BY artifacts.artifact_id
        """
    )
    grouped: dict[int, dict[str, Any]] = {}
    for row in rows:
        item = grouped.setdefault(
            row["artifact_id"],
            {
                "artifact_id": row["artifact_id"],
                "title": row["title"],
                "kind": row["kind"],
                "facet": row["facet"],
                "relation": row["relation"],
                "source_path": row["source_path"],
                "line": row["line"],
                "summary": row["summary"],
                "content": row["content"],
                "qualified_name": row["qualified_name"],
                "topic_ids": [],
                "evidence_sources": [],
                "link_weight": 0.0,
                "max_weight": 0.0,
            },
        )
        if row["topic_id"] is not None:
            item["topic_ids"].append(row["topic_id"])
            item["evidence_sources"].append(row["evidence_source"])
            item["link_weight"] += float(row["weight"])
            item["max_weight"] = max(item["max_weight"], float(row["weight"]))
    return grouped


def _facet_bonus(facet: DevTopicFacet) -> float:
    return float(FACET_PRIORITY[facet]) * 3.0


def search_topics(
    query: str,
    facets: list[DevTopicFacet] | None = None,
    *,
    limit: int = 20,
    db_path: str | Path | None = None,
) -> SearchResponse:
    """Search developer topics and ranked artifacts."""

    db = _ensure_db(db_path)
    terms, requested_facets = _parse_query(query, facets)
    topic_hits = _topic_matches(terms)
    matched_topic_ids = {item.topic_id for item in topic_hits}
    fts_scores = _fts_scores(db, terms)
    artifact_rows = _all_artifact_hits(db)

    results: list[ArtifactHit] = []
    normalized_terms = [normalize_text(term) for term in terms]
    for artifact in artifact_rows.values():
        if requested_facets and artifact["facet"] not in requested_facets:
            continue
        title_norm = normalize_text(artifact["title"])
        summary_norm = normalize_text(artifact["summary"])
        qname_norm = normalize_text(artifact["qualified_name"] or "")
        path_norm = normalize_text(artifact["source_path"])
        lexical = 0.0
        if normalized_terms and all(
            any(term in hay for hay in (title_norm, summary_norm, qname_norm, path_norm))
            for term in normalized_terms
        ):
            lexical = 25.0
        topic_bonus = 0.0
        if matched_topic_ids:
            overlap = matched_topic_ids.intersection(artifact["topic_ids"])
            if not overlap:
                if lexical <= 0:
                    continue
            else:
                topic_bonus = 60.0 + 10.0 * len(overlap)
        elif lexical <= 0 and artifact["link_weight"] <= 0:
            continue
        score = artifact["max_weight"] + topic_bonus + lexical + _facet_bonus(artifact["facet"])
        score += fts_scores.get(artifact["artifact_id"], 0.0)
        results.append(
            ArtifactHit(
                artifact_id=artifact["artifact_id"],
                title=artifact["title"],
                kind=artifact["kind"],
                facet=artifact["facet"],
                relation=artifact["relation"],
                source_path=artifact["source_path"],
                line=artifact["line"],
                summary=artifact["summary"],
                score=score,
                topic_ids=sorted(set(artifact["topic_ids"])),
                evidence_sources=sorted(set(artifact["evidence_sources"])),
                qualified_name=artifact["qualified_name"],
            )
        )

    results.sort(
        key=lambda item: (-item.score, -FACET_PRIORITY[item.facet], item.title.lower(), item.source_path)
    )
    return SearchResponse(
        query=query,
        parsed_terms=terms,
        inferred_facets=[] if facets else requested_facets,
        requested_facets=list(facets or []),
        topics=topic_hits[:limit],
        artifacts=results[:limit],
    )


def get_topic_map(
    topic_id: str,
    *,
    limit: int = 24,
    db_path: str | Path | None = None,
) -> TopicMap:
    """Return one topic, related topics, and linked artifacts."""

    db = _ensure_db(db_path)
    topics = {topic.topic_id: topic for topic in load_topics()}
    if topic_id not in topics:
        raise KeyError(f"Unknown dev topic: {topic_id}")
    topic = topics[topic_id]
    related = [topics[item] for item in topic.related_topic_ids if item in topics]

    rows = db.load_rows(
        """
        SELECT
            artifacts.artifact_id,
            artifacts.title,
            artifacts.kind,
            artifacts.facet,
            artifacts.relation,
            artifacts.source_path,
            artifacts.line,
            artifacts.summary,
            artifacts.qualified_name,
            SUM(artifact_topics.weight) AS weight,
            GROUP_CONCAT(artifact_topics.evidence_source) AS evidence_sources
        FROM artifacts
        JOIN artifact_topics ON artifact_topics.artifact_id = artifacts.artifact_id
        WHERE artifact_topics.topic_id = ?
        GROUP BY artifacts.artifact_id
        ORDER BY weight DESC, artifacts.title ASC
        LIMIT ?
        """,
        (topic_id, limit),
    )
    artifacts = [
        ArtifactHit(
            artifact_id=row["artifact_id"],
            title=row["title"],
            kind=row["kind"],
            facet=row["facet"],
            relation=row["relation"],
            source_path=row["source_path"],
            line=row["line"],
            summary=row["summary"],
            score=float(row["weight"]) + _facet_bonus(row["facet"]),
            topic_ids=[topic_id],
            evidence_sources=sorted(set((row["evidence_sources"] or "").split(","))) if row["evidence_sources"] else [],
            qualified_name=row["qualified_name"],
        )
        for row in rows
    ]
    artifact_ids = tuple(item.artifact_id for item in artifacts)
    links: list[TopicGraphLink] = []
    if artifact_ids:
        placeholders = ", ".join("?" for _ in artifact_ids)
        link_rows = db.load_rows(
            f"""
            SELECT source_artifact_id, target_artifact_id, link_kind
            FROM artifact_links
            WHERE source_artifact_id IN ({placeholders})
              AND target_artifact_id IN ({placeholders})
            ORDER BY source_artifact_id, target_artifact_id, link_kind
            """,
            artifact_ids + artifact_ids,
        )
        links = [
            TopicGraphLink(
                link_kind=row["link_kind"],
                source_artifact_id=row["source_artifact_id"],
                target_artifact_id=row["target_artifact_id"],
            )
            for row in link_rows
        ]
    return TopicMap(topic=topic, related_topics=related, artifacts=artifacts, links=links)


def build_context_pack(
    topic_ids: list[str],
    facets: list[DevTopicFacet] | None = None,
    *,
    limit: int = 12,
    db_path: str | Path | None = None,
) -> ContextPack:
    """Build a compact ordered context pack for one or more developer topics."""

    db = _ensure_db(db_path)
    topics = {topic.topic_id: topic for topic in load_topics()}
    unknown = [topic_id for topic_id in topic_ids if topic_id not in topics]
    if unknown:
        raise KeyError(f"Unknown dev topics: {', '.join(sorted(unknown))}")

    placeholders = ", ".join("?" for _ in topic_ids)
    params: tuple[Any, ...]
    query = f"""
        SELECT
            artifacts.title,
            artifacts.facet,
            artifacts.relation,
            artifacts.source_path,
            artifacts.line,
            artifacts.summary,
            artifacts.qualified_name,
            GROUP_CONCAT(DISTINCT artifact_topics.topic_id) AS topic_ids,
            SUM(artifact_topics.weight) AS weight
        FROM artifacts
        JOIN artifact_topics ON artifact_topics.artifact_id = artifacts.artifact_id
        WHERE artifact_topics.topic_id IN ({placeholders})
    """
    params = tuple(topic_ids)
    if facets:
        facet_placeholders = ", ".join("?" for _ in facets)
        query += f" AND artifacts.facet IN ({facet_placeholders})"
        params = params + tuple(facets)
    query += """
        GROUP BY artifacts.artifact_id
        ORDER BY artifacts.title ASC
    """
    rows = db.load_rows(query, params)
    items = [
        ContextPackItem(
            title=row["title"],
            facet=row["facet"],
            relation=row["relation"],
            source_path=row["source_path"],
            line=row["line"],
            summary=row["summary"],
            topic_ids=sorted(set((row["topic_ids"] or "").split(","))) if row["topic_ids"] else [],
            qualified_name=row["qualified_name"],
        )
        for row in rows
    ]
    items.sort(
        key=lambda item: (
            -FACET_PRIORITY[item.facet],
            item.title.lower(),
            item.source_path,
        )
    )
    return ContextPack(topic_ids=topic_ids, facets=list(facets or []), items=items[:limit])
