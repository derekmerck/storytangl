from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import Field

from tangl.core._pydantic import BaseModelPlus


DevTopicFacet = Literal[
    "overview",
    "design",
    "api",
    "code",
    "tests",
    "demos",
    "governance",
    "notes",
]
DevTopicRelation = Literal[
    "defines",
    "documents",
    "tests",
    "demonstrates",
    "governs",
    "mentions",
]
ArtifactKind = Literal[
    "doc_section",
    "api_page",
    "symbol",
    "test_module",
    "demo_asset",
    "governance_doc",
    "note",
    "issue",
]


class TopicDefinition(BaseModelPlus):
    """Curated developer-topic definition used by the local reference index."""

    topic_id: str
    display_name: str
    aliases: list[str] = Field(default_factory=list)
    layer: str
    short_description: str
    related_topic_ids: list[str] = Field(default_factory=list)


class BuildReport(BaseModelPlus):
    """Summary of a build or refresh operation."""

    db_path: str
    build_mode: Literal["full", "incremental", "noop"]
    indexed_sources: int
    changed_sources: int
    removed_sources: int
    artifacts: int
    symbols: int
    topic_links: int
    artifact_links: int
    used_fts: bool


class TopicHit(BaseModelPlus):
    """One ranked topic match returned by search."""

    topic_id: str
    display_name: str
    layer: str
    short_description: str
    score: float
    matched_alias: str | None = None


class ArtifactHit(BaseModelPlus):
    """One ranked artifact hit linked to one or more developer topics."""

    artifact_id: int
    title: str
    kind: ArtifactKind
    facet: DevTopicFacet
    relation: DevTopicRelation
    source_path: str
    line: int | None = None
    summary: str
    score: float
    topic_ids: list[str] = Field(default_factory=list)
    evidence_sources: list[str] = Field(default_factory=list)
    qualified_name: str | None = None


class SearchResponse(BaseModelPlus):
    """Search results containing matched topics and ranked artifact hits."""

    query: str
    parsed_terms: list[str]
    inferred_facets: list[DevTopicFacet] = Field(default_factory=list)
    requested_facets: list[DevTopicFacet] = Field(default_factory=list)
    topics: list[TopicHit] = Field(default_factory=list)
    artifacts: list[ArtifactHit] = Field(default_factory=list)


class TopicGraphLink(BaseModelPlus):
    """A graph edge between artifacts or topics in the reference map."""

    link_kind: str
    source_artifact_id: int
    target_artifact_id: int


class TopicMap(BaseModelPlus):
    """Topic-centered graph view with related topics and linked artifacts."""

    topic: TopicDefinition
    related_topics: list[TopicDefinition] = Field(default_factory=list)
    artifacts: list[ArtifactHit] = Field(default_factory=list)
    links: list[TopicGraphLink] = Field(default_factory=list)


class ContextPackItem(BaseModelPlus):
    """One compact context-pack item prepared for agent retrieval."""

    title: str
    facet: DevTopicFacet
    relation: DevTopicRelation
    source_path: str
    line: int | None = None
    summary: str
    topic_ids: list[str] = Field(default_factory=list)
    qualified_name: str | None = None


class ContextPack(BaseModelPlus):
    """Compact ordered context pack for one or more developer topics."""

    topic_ids: list[str]
    facets: list[DevTopicFacet] = Field(default_factory=list)
    items: list[ContextPackItem] = Field(default_factory=list)


class TopicAnnotation(BaseModelPlus):
    """Manual annotation parsed from docs, markdown, or docstrings."""

    topics: list[str]
    facets: list[DevTopicFacet] = Field(default_factory=list)
    relation: DevTopicRelation
    related: list[str] = Field(default_factory=list)


class ExtractedArtifact(BaseModelPlus):
    """Intermediate artifact extracted from one source file."""

    source_path: str
    source_hash: str
    artifact_key: str
    title: str
    kind: ArtifactKind
    facet: DevTopicFacet
    relation: DevTopicRelation
    line: int | None = None
    anchor: str | None = None
    summary: str
    content: str = ""
    qualified_name: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class ExtractedSymbol(BaseModelPlus):
    """Intermediate symbol record extracted from a Python source file."""

    qualified_name: str
    symbol_kind: str
    module_name: str
    object_name: str
    source_path: str
    source_hash: str
    line: int | None = None
    signature: str | None = None
    summary: str = ""


class BuildConfig(BaseModelPlus):
    """Configurable filesystem locations for devref builds."""

    repo_root: str
    db_path: str
    incremental: bool = True

    @property
    def repo_root_path(self) -> Path:
        return Path(self.repo_root)

    @property
    def db_file(self) -> Path:
        return Path(self.db_path)
