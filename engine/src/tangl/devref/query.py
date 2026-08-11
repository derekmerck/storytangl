from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, NamedTuple

from .builder import DEFAULT_DB_PATH, FACET_PRIORITY, build_index, normalize_text
from .models import (
    ArtifactHit,
    ContextPack,
    ContextPackItem,
    DevTopicFacet,
    DevTopicRelation,
    SearchResponse,
    TopicDefinition,
    TopicGraphLink,
    TopicHit,
    TopicMap,
)
from .storage import DevRefDatabase
from .topics import load_topics


RELATION_PRIORITY: dict[DevTopicRelation, int] = {
    "defines": 60,
    "governs": 50,
    "documents": 40,
    "tests": 30,
    "demonstrates": 20,
    "mentions": 10,
}


class _TopicLink(NamedTuple):
    topic_id: str
    facet: DevTopicFacet
    relation: DevTopicRelation
    evidence_source: str
    weight: float


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


def _quote_fts_term(term: str) -> str:
    escaped = term.replace('"', '""')
    return f'"{escaped}"'


def _fts_scores(db: DevRefDatabase, terms: list[str]) -> dict[int, float]:
    if not terms:
        return {}
    meta = db.get_meta()
    if meta.get("used_fts") != "1":
        return {}
    safe_terms = [_quote_fts_term(term) for term in terms if term]
    if not safe_terms:
        return {}
    query = " ".join(safe_terms)
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


def _topic_link(row: sqlite3.Row) -> _TopicLink:
    return _TopicLink(
        topic_id=row["topic_id"],
        facet=row["topic_facet"],
        relation=row["topic_relation"],
        evidence_source=row["evidence_source"],
        weight=float(row["weight"]),
    )


def _group_topic_rows(
    rows: list[sqlite3.Row],
) -> list[tuple[sqlite3.Row, list[_TopicLink]]]:
    grouped: dict[int, tuple[sqlite3.Row, list[_TopicLink]]] = {}
    for row in rows:
        item = grouped.setdefault(row["artifact_id"], (row, []))
        item[1].append(_topic_link(row))
    return list(grouped.values())


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
            artifact_topics.facet AS topic_facet,
            artifact_topics.relation AS topic_relation,
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
                "topic_links": [],
                "topic_ids": [],
                "evidence_sources": [],
                "link_weight": 0.0,
                "max_weight": 0.0,
            },
        )
        if row["topic_id"] is not None:
            item["topic_links"].append(_topic_link(row))
            item["topic_ids"].append(row["topic_id"])
            item["evidence_sources"].append(row["evidence_source"])
            item["link_weight"] += float(row["weight"])
            item["max_weight"] = max(item["max_weight"], float(row["weight"]))
    return grouped


def _best_topic_link(links: list[_TopicLink]) -> _TopicLink:
    """Choose one topic-relative classification for a returned artifact."""

    return max(
        links,
        key=lambda link: (
            link.weight,
            FACET_PRIORITY[link.facet],
            RELATION_PRIORITY[link.relation],
            link.topic_id,
        ),
    )


def _classifying_topic_links(links: list[_TopicLink]) -> list[_TopicLink]:
    """Let manual annotations replace inferred classification for one topic."""

    manual_topics = {
        link.topic_id
        for link in links
        if link.evidence_source == "manual_annotation"
    }
    return [
        link
        for link in links
        if link.evidence_source == "manual_annotation"
        or link.topic_id not in manual_topics
    ]


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
        topic_links = _classifying_topic_links(artifact["topic_links"])
        matching_links = [
            link for link in topic_links if link.topic_id in matched_topic_ids
        ]
        if matched_topic_ids:
            overlap = matched_topic_ids.intersection(artifact["topic_ids"])
            if not overlap:
                if lexical <= 0:
                    continue
            else:
                topic_bonus = 60.0 + 10.0 * len(overlap)
        elif lexical <= 0 and artifact["link_weight"] <= 0:
            continue

        effective_links = matching_links if matching_links else topic_links
        if requested_facets:
            effective_links = [
                link for link in effective_links if link.facet in requested_facets
            ]
            if not effective_links:
                # Unlinked artifacts may still match their file-level facet;
                # topic-linked artifacts must match one of their own links.
                if topic_links or artifact["facet"] not in requested_facets:
                    continue

        if effective_links and (matched_topic_ids or requested_facets):
            best_link = _best_topic_link(effective_links)
            facet = best_link.facet
            relation = best_link.relation
            link_weight = max(link.weight for link in effective_links)
        else:
            facet = artifact["facet"]
            relation = artifact["relation"]
            link_weight = artifact["max_weight"]

        score = link_weight + topic_bonus + lexical + _facet_bonus(facet)
        score += fts_scores.get(artifact["artifact_id"], 0.0)
        results.append(
            ArtifactHit(
                artifact_id=artifact["artifact_id"],
                title=artifact["title"],
                kind=artifact["kind"],
                facet=facet,
                relation=relation,
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
            artifact_topics.topic_id,
            artifact_topics.facet AS topic_facet,
            artifact_topics.relation AS topic_relation,
            artifact_topics.evidence_source,
            artifact_topics.weight
        FROM artifacts
        JOIN artifact_topics ON artifact_topics.artifact_id = artifacts.artifact_id
        WHERE artifact_topics.topic_id = ?
        ORDER BY artifacts.artifact_id
        """,
        (topic_id,),
    )
    artifacts: list[ArtifactHit] = []
    for row, links in _group_topic_rows(rows):
        links = _classifying_topic_links(links)
        best_link = _best_topic_link(links)
        score = sum(link.weight for link in links)
        score += _facet_bonus(best_link.facet)
        artifacts.append(
            ArtifactHit(
                artifact_id=row["artifact_id"],
                title=row["title"],
                kind=row["kind"],
                facet=best_link.facet,
                relation=best_link.relation,
                source_path=row["source_path"],
                line=row["line"],
                summary=row["summary"],
                score=score,
                topic_ids=[topic_id],
                evidence_sources=sorted({link.evidence_source for link in links}),
                qualified_name=row["qualified_name"],
            )
        )
    artifacts.sort(
        key=lambda item: (
            -item.score,
            -FACET_PRIORITY[item.facet],
            item.title.lower(),
            item.source_path,
        )
    )
    artifacts = artifacts[:limit]
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
            artifacts.artifact_id,
            artifacts.title,
            artifacts.source_path,
            artifacts.line,
            artifacts.summary,
            artifacts.qualified_name,
            artifact_topics.topic_id,
            artifact_topics.facet AS topic_facet,
            artifact_topics.relation AS topic_relation,
            artifact_topics.evidence_source,
            artifact_topics.weight
        FROM artifacts
        JOIN artifact_topics ON artifact_topics.artifact_id = artifacts.artifact_id
        WHERE artifact_topics.topic_id IN ({placeholders})
    """
    params = tuple(topic_ids)
    query += " ORDER BY artifacts.artifact_id"
    rows = db.load_rows(query, params)

    items: list[ContextPackItem] = []
    for row, links in _group_topic_rows(rows):
        links = _classifying_topic_links(links)
        if facets:
            links = [link for link in links if link.facet in facets]
        if not links:
            continue
        best_link = _best_topic_link(links)
        items.append(
            ContextPackItem(
                title=row["title"],
                facet=best_link.facet,
                relation=best_link.relation,
                source_path=row["source_path"],
                line=row["line"],
                summary=row["summary"],
                topic_ids=sorted({link.topic_id for link in links}),
                qualified_name=row["qualified_name"],
            )
        )
    items.sort(
        key=lambda item: (
            -FACET_PRIORITY[item.facet],
            item.title.lower(),
            item.source_path,
        )
    )
    return ContextPack(topic_ids=topic_ids, facets=list(facets or []), items=items[:limit])
