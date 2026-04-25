from __future__ import annotations

import ast
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import importlib
import inspect
import json
import logging
import re
from pathlib import Path
from typing import Any

from .annotations import extract_storytangl_topic_annotations
from .models import (
    BuildReport,
    DevTopicFacet,
    DevTopicRelation,
    ExtractedArtifact,
    ExtractedSymbol,
    TopicAnnotation,
    TopicDefinition,
)
from .storage import DevRefDatabase
from .topics import load_topics, topic_registry_hash


logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_DB_PATH = REPO_ROOT / "tmp" / "devref" / "devref.sqlite3"
BUILDER_VERSION = "1"
FACET_PRIORITY: dict[DevTopicFacet, int] = {
    "overview": 100,
    "design": 90,
    "api": 80,
    "code": 70,
    "tests": 60,
    "demos": 50,
    "governance": 40,
    "notes": 30,
}
HEADING_CHARS = {"=", "-", "~", "^", '"', "*", "+"}
AUTODOC_RE = re.compile(
    r"(?m)^\s*\.\.\s+auto(?:class|function|module|method|attribute|data)::\s+([A-Za-z0-9_\.]+)\s*$"
)
DOC_LINK_RE = re.compile(r":doc:`(?:[^`<]+<)?([^`>]+)>?`")
MD_LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
SIMPLE_ROLE_RE = re.compile(r":[a-zA-Z0-9_]+:`([^`]+)`")
SENTENCE_RE = re.compile(r"(?s)(.+?[\.\!\?])(?:\s|$)")
TEXT_SPLIT_RE = re.compile(r"[^a-z0-9]+")


@dataclass(frozen=True)
class _Section:
    title: str
    line: int
    anchor: str
    text: str


def normalize_text(value: str) -> str:
    """Normalize text for topic and lexical matching."""

    lowered = value.lower().replace("_", " ")
    return " ".join(part for part in TEXT_SPLIT_RE.split(lowered) if part)


def slugify(value: str) -> str:
    """Build a stable anchor slug from a title."""

    return "-".join(part for part in normalize_text(value).split())


def summarize_text(value: str) -> str:
    """Return a compact one-sentence summary from raw text."""

    cleaned = SIMPLE_ROLE_RE.sub(r"\1", value).strip()
    if not cleaned:
        return ""
    match = SENTENCE_RE.match(cleaned.replace("\n", " ").strip())
    return match.group(1).strip() if match is not None else cleaned[:200].strip()


def first_paragraph(text: str) -> str:
    """Return the first non-heading paragraph from section text."""

    lines = text.splitlines()
    if len(lines) >= 2 and _is_heading_underline(lines[1]):
        text = "\n".join(lines[2:])
    elif lines and lines[0].lstrip().startswith("#"):
        text = "\n".join(lines[1:])

    paragraphs: list[str] = []
    block: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            if block:
                paragraphs.append(" ".join(block))
                block = []
            continue
        if line.startswith(".. storytangl-topic::") or line.startswith("```{storytangl-topic}"):
            continue
        if line.startswith(":") and block == []:
            continue
        if line.startswith(".. ") and block == []:
            continue
        if line.startswith("#"):
            continue
        block.append(line)
    if block:
        paragraphs.append(" ".join(block))
    return paragraphs[0] if paragraphs else ""


def sha256_text(value: str) -> str:
    """Return the SHA-256 hex digest for text content."""

    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def file_hash(path: Path) -> str:
    """Return the SHA-256 hex digest for one file."""

    return hashlib.sha256(path.read_bytes()).hexdigest()


def default_db_path() -> Path:
    """Return the default SQLite path used by the devref system."""

    return DEFAULT_DB_PATH


def _is_heading_underline(line: str) -> bool:
    stripped = line.strip()
    return len(stripped) >= 3 and len(set(stripped)) == 1 and stripped[0] in HEADING_CHARS


def parse_sections(path: Path, text: str) -> list[_Section]:
    """Split markdown or reStructuredText source into heading-sized sections."""

    if path.suffix.lower() in {".md", ".markdown"}:
        return _parse_markdown_sections(path, text)
    if path.suffix.lower() == ".rst":
        return _parse_rst_sections(path, text)
    return [
        _Section(
            title=path.stem.replace("_", " "),
            line=1,
            anchor=slugify(path.stem),
            text=text,
        )
    ]


def _parse_markdown_sections(path: Path, text: str) -> list[_Section]:
    lines = text.splitlines()
    headings: list[tuple[int, str]] = []
    for index, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not stripped.startswith("#"):
            continue
        title = stripped.lstrip("#").strip()
        if title:
            headings.append((index, title))

    if not headings:
        return [_Section(title=path.stem, line=1, anchor=slugify(path.stem), text=text)]

    sections: list[_Section] = []
    for pos, (line_no, title) in enumerate(headings):
        next_line = headings[pos + 1][0] - 1 if pos + 1 < len(headings) else len(lines)
        section_text = "\n".join(lines[line_no - 1:next_line]).strip()
        sections.append(_Section(title=title, line=line_no, anchor=slugify(title), text=section_text))
    return sections


def _parse_rst_sections(path: Path, text: str) -> list[_Section]:
    lines = text.splitlines()
    headings: list[tuple[int, str]] = []
    for index in range(len(lines) - 1):
        title = lines[index].rstrip()
        underline = lines[index + 1].rstrip()
        if not title.strip():
            continue
        if _is_heading_underline(underline) and len(underline.strip()) >= len(title.strip()):
            headings.append((index + 1, title.strip()))

    if not headings:
        return [_Section(title=path.stem, line=1, anchor=slugify(path.stem), text=text)]

    sections: list[_Section] = []
    for pos, (line_no, title) in enumerate(headings):
        next_line = headings[pos + 1][0] - 1 if pos + 1 < len(headings) else len(lines)
        section_text = "\n".join(lines[line_no - 1:next_line]).strip()
        sections.append(_Section(title=title, line=line_no, anchor=slugify(title), text=section_text))
    return sections


def classify_source(path: Path, repo_root: Path) -> tuple[str, DevTopicFacet, DevTopicRelation]:
    """Classify a source file into artifact family defaults."""

    parts = path.parts
    path_str = path.as_posix()
    if path.name == "AGENTS.md":
        if "engine/tests" in path_str:
            return "governance_doc", "tests", "governs"
        return "governance_doc", "governance", "governs"
    if path.name == "ARCHITECTURE.md":
        return "doc_section", "overview", "documents"
    if "docs/src/api/" in path_str:
        return "api_page", "api", "documents"
    if path.suffix.lower() == ".py" and "tests" in parts:
        return "test_module", "tests", "tests"
    if path.is_relative_to(repo_root / "worlds"):
        return "demo_asset", "demos", "demonstrates"
    if path.name.endswith("_DESIGN.md") or "docs/src/design/" in path_str:
        return "doc_section", "design", "documents"
    if "notes" in parts:
        return "note", "notes", "mentions"
    if path.name == "__init__.py":
        return "doc_section", "overview", "documents"
    return "doc_section", "notes", "mentions"


def resolve_doc_target(source_path: Path, target: str, repo_root: Path) -> str | None:
    """Resolve a local doc link to a concrete repo-relative path."""

    cleaned = target.strip()
    if not cleaned or "://" in cleaned or cleaned.startswith("#"):
        return None
    base = source_path.parent
    candidate = (base / cleaned).resolve()
    for option in (candidate, candidate.with_suffix(".rst"), candidate.with_suffix(".md")):
        try:
            rel = option.relative_to(repo_root)
        except ValueError:
            continue
        if option.exists():
            return rel.as_posix()
    return None


def extract_related_paths(source_path: Path, text: str, repo_root: Path) -> list[str]:
    """Extract local cross-doc links from one source block."""

    matches: list[str] = []
    for pattern in (DOC_LINK_RE, MD_LINK_RE):
        for match in pattern.finditer(text):
            target = resolve_doc_target(source_path, match.group(1), repo_root)
            if target is not None:
                matches.append(target)
    return sorted(set(matches))


def extract_symbol_refs(text: str) -> list[str]:
    """Extract autodoc-style fully qualified symbol references."""

    return sorted(set(match.group(1).strip() for match in AUTODOC_RE.finditer(text)))


def module_name_for_path(path: Path, repo_root: Path) -> str | None:
    """Resolve a Python module name from one source path."""

    roots = [
        repo_root / "engine" / "src",
        repo_root / "apps" / "cli" / "src",
        repo_root / "apps" / "server" / "src",
        repo_root / "apps" / "renpy" / "src",
    ]
    for root in roots:
        try:
            rel = path.relative_to(root)
        except ValueError:
            continue
        return ".".join(rel.with_suffix("").parts)
    return None


def iter_source_paths(repo_root: Path) -> list[Path]:
    """Collect all repo-local source files covered by the v1 devref index."""

    patterns = [
        "AGENTS.md",
        "ARCHITECTURE.md",
        "engine/tests/AGENTS.md",
        "docs/src/**/*.md",
        "docs/src/**/*.rst",
        "engine/src/**/*.py",
        "engine/src/**/*_DESIGN.md",
        "engine/src/**/notes.md",
        "engine/tests/**/*.py",
        "apps/**/AGENTS.md",
        "apps/**/notes/**/*.md",
        "apps/**/notes/**/*.rst",
        "apps/**/src/**/*.py",
        "apps/**/tests/**/*.py",
        "worlds/**/*.md",
        "worlds/**/*.yaml",
        "worlds/**/*.twee",
    ]
    found: set[Path] = set()
    for pattern in patterns:
        found.update(path for path in repo_root.glob(pattern) if path.is_file())
    return sorted(
        path for path in found
        if "__pycache__" not in path.parts and ".pytest_cache" not in path.parts
    )


def _import_module(module_name: str) -> Any | None:
    try:
        return importlib.import_module(module_name)
    except Exception:
        logger.debug(
            "Skipping live import during devref indexing: %s",
            module_name,
            exc_info=True,
        )
        return None


def _signature_for_object(obj: Any) -> str | None:
    if not callable(obj):
        return None
    try:
        return str(inspect.signature(obj))
    except (TypeError, ValueError):
        return None


def _line_for_object(obj: Any, fallback: int | None) -> int | None:
    try:
        _, line = inspect.getsourcelines(obj)
        return int(line)
    except (OSError, TypeError):
        return fallback


def _summary_for_object(obj: Any, fallback: str) -> str:
    doc = inspect.getdoc(obj) or fallback
    return summarize_text(doc)


def extract_python_source(
    path: Path,
    source_hash: str,
    repo_root: Path,
    *,
    live_imports: bool = False,
) -> tuple[list[ExtractedArtifact], list[ExtractedSymbol]]:
    """Extract module overview/test artifacts and public symbols from Python source."""

    try:
        text = path.read_text(encoding="utf-8")
        tree = ast.parse(text)
    except (SyntaxError, UnicodeDecodeError) as exc:
        logger.warning(
            "Skipping unreadable Python source during devref indexing: %s (%s)",
            path,
            exc,
        )
        return [], []
    module_name = module_name_for_path(path, repo_root)
    module_doc = ast.get_docstring(tree, clean=False) or ""
    artifacts: list[ExtractedArtifact] = []
    symbols: list[ExtractedSymbol] = []

    if module_doc and (path.name == "__init__.py" or "tests" in path.parts):
        kind, facet, relation = classify_source(path, repo_root)
        title = module_name or path.stem
        if "tests" in path.parts:
            title = module_doc.splitlines()[0].strip().strip('"`') if module_doc else path.stem
        artifacts.append(
            ExtractedArtifact(
                source_path=path.relative_to(repo_root).as_posix(),
                source_hash=source_hash,
                artifact_key=f"{path.relative_to(repo_root).as_posix()}#module",
                title=title,
                kind=kind,
                facet=facet,
                relation=relation,
                line=1,
                anchor="module",
                summary=summarize_text(module_doc),
                content=module_doc,
                metadata={
                    "annotations": [item.model_dump(mode="python") for item in extract_storytangl_topic_annotations(module_doc)],
                    "related_paths": [],
                    "symbol_refs": [],
                },
            )
        )

    if module_name is None or "tests" in path.parts:
        return artifacts, symbols

    module = _import_module(module_name) if live_imports else None
    source_path = path.relative_to(repo_root).as_posix()
    for node in tree.body:
        if not isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if node.name.startswith("_"):
            continue
        symbol_obj = getattr(module, node.name, None) if module is not None else None
        qualified_name = (
            f"{symbol_obj.__module__}.{symbol_obj.__qualname__}"
            if symbol_obj is not None and hasattr(symbol_obj, "__qualname__")
            else f"{module_name}.{node.name}"
        )
        docstring = ast.get_docstring(node, clean=False) or ""
        summary = (
            _summary_for_object(symbol_obj, docstring)
            if symbol_obj is not None
            else summarize_text(docstring)
        )
        symbol = ExtractedSymbol(
            qualified_name=qualified_name,
            symbol_kind="class" if isinstance(node, ast.ClassDef) else "function",
            module_name=module_name,
            object_name=node.name,
            source_path=source_path,
            source_hash=source_hash,
            line=_line_for_object(symbol_obj, node.lineno) if symbol_obj is not None else node.lineno,
            signature=_signature_for_object(symbol_obj) if symbol_obj is not None else None,
            summary=summary,
        )
        symbols.append(symbol)
        artifacts.append(
            ExtractedArtifact(
                source_path=source_path,
                source_hash=source_hash,
                artifact_key=f"symbol:{qualified_name}",
                title=node.name,
                kind="symbol",
                facet="code",
                relation="defines",
                line=symbol.line,
                anchor=slugify(node.name),
                summary=summary,
                content=(ast.get_docstring(node, clean=False) or "").strip(),
                qualified_name=qualified_name,
                metadata={
                    "annotations": [],
                    "related_paths": [],
                    "symbol_refs": [qualified_name],
                    "module_name": module_name,
                },
            )
        )
    return artifacts, symbols


def extract_text_source(path: Path, source_hash: str, repo_root: Path) -> list[ExtractedArtifact]:
    """Extract heading-sized artifacts from markdown, RST, YAML, and demo text files."""

    text = path.read_text(encoding="utf-8")
    kind, facet, relation = classify_source(path, repo_root)
    source_path = path.relative_to(repo_root).as_posix()
    sections = parse_sections(path, text)
    artifacts: list[ExtractedArtifact] = []
    for section in sections:
        annotations = extract_storytangl_topic_annotations(section.text)
        metadata = {
            "annotations": [item.model_dump(mode="python") for item in annotations],
            "related_paths": extract_related_paths(path, section.text, repo_root),
            "symbol_refs": extract_symbol_refs(section.text),
        }
        artifacts.append(
            ExtractedArtifact(
                source_path=source_path,
                source_hash=source_hash,
                artifact_key=f"{source_path}#{section.anchor}",
                title=section.title,
                kind=kind,
                facet=facet,
                relation=relation,
                line=section.line,
                anchor=section.anchor,
                summary=summarize_text(first_paragraph(section.text) or section.text),
                content=section.text,
                metadata=metadata,
            )
        )
    return artifacts


def extract_source_file(
    path: Path,
    source_hash: str,
    repo_root: Path,
    *,
    live_imports: bool = False,
) -> tuple[list[ExtractedArtifact], list[ExtractedSymbol]]:
    """Extract all supported artifacts and symbols from one source path."""

    if path.suffix.lower() == ".py":
        return extract_python_source(
            path,
            source_hash,
            repo_root,
            live_imports=live_imports,
        )
    return extract_text_source(path, source_hash, repo_root), []


def topic_related_map(topics: list[TopicDefinition]) -> dict[str, TopicDefinition]:
    """Index topic definitions by id for quick lookup."""

    return {topic.topic_id: topic for topic in topics}


def match_alias(text: str, alias_norm: str) -> bool:
    """Return whether one normalized alias appears as a token sequence in text."""

    if not alias_norm:
        return False
    padded = f" {text} "
    return f" {alias_norm} " in padded


def _annotation_links(
    artifact_id: int,
    annotations: list[TopicAnnotation],
    default_facet: DevTopicFacet,
    default_relation: DevTopicRelation,
    topic_ids: set[str],
) -> list[tuple[int, str, str, str, str, float]]:
    rows: list[tuple[int, str, str, str, str, float]] = []
    for annotation in annotations:
        for topic_id in annotation.topics:
            if topic_id not in topic_ids:
                continue
            facets = annotation.facets or [default_facet]
            for facet in facets:
                rows.append(
                    (
                        artifact_id,
                        topic_id,
                        facet,
                        annotation.relation,
                        "manual_annotation",
                        120.0,
                    )
                )
    return rows


def _symbol_links(
    artifact_id: int,
    symbol_refs: list[str],
    default_facet: DevTopicFacet,
    default_relation: DevTopicRelation,
    topics: list[TopicDefinition],
) -> list[tuple[int, str, str, str, str, float]]:
    rows: list[tuple[int, str, str, str, str, float]] = []
    refs = [normalize_text(ref) for ref in symbol_refs]
    for topic in topics:
        alias_norms = {normalize_text(topic.topic_id), normalize_text(topic.display_name)}
        alias_norms.update(normalize_text(alias) for alias in topic.aliases)
        if any(any(match_alias(ref, alias_norm) for alias_norm in alias_norms) for ref in refs):
            rows.append(
                (
                    artifact_id,
                    topic.topic_id,
                    default_facet,
                    default_relation,
                    "autodoc_symbol",
                    95.0,
                )
            )
    return rows


def _heuristic_links(
    artifact_id: int,
    title: str,
    summary: str,
    content: str,
    source_path: str,
    qualified_name: str | None,
    kind: str,
    default_facet: DevTopicFacet,
    default_relation: DevTopicRelation,
    topics: list[TopicDefinition],
) -> list[tuple[int, str, str, str, str, float]]:
    rows: list[tuple[int, str, str, str, str, float]] = []
    title_norm = normalize_text(title)
    summary_norm = normalize_text(summary)
    content_norm = normalize_text(content[:2000])
    path_norm = normalize_text(source_path)
    qname_norm = normalize_text(qualified_name or "")
    for topic in topics:
        alias_norms = {normalize_text(topic.topic_id), normalize_text(topic.display_name)}
        alias_norms.update(normalize_text(alias) for alias in topic.aliases)
        matched = False
        for alias_norm in alias_norms:
            if not alias_norm:
                continue
            if match_alias(title_norm, alias_norm):
                rows.append((artifact_id, topic.topic_id, default_facet, default_relation, "title_match", 75.0))
                matched = True
                break
        if matched:
            continue
        for alias_norm in alias_norms:
            if not alias_norm:
                continue
            if match_alias(qname_norm, alias_norm):
                rows.append((artifact_id, topic.topic_id, default_facet, default_relation, "qname_match", 68.0))
                matched = True
                break
        if matched:
            continue
        for alias_norm in alias_norms:
            if not alias_norm:
                continue
            if match_alias(summary_norm, alias_norm) or match_alias(content_norm, alias_norm):
                rows.append((artifact_id, topic.topic_id, default_facet, default_relation, "content_match", 38.0))
                matched = True
                break
        if matched:
            continue
        for alias_norm in alias_norms:
            if not alias_norm:
                continue
            if match_alias(path_norm, alias_norm):
                evidence = "test_heuristic" if kind == "test_module" else "demo_heuristic" if kind == "demo_asset" else "path_match"
                weight = 34.0 if kind == "test_module" else 30.0 if kind == "demo_asset" else 28.0
                rows.append((artifact_id, topic.topic_id, default_facet, default_relation, evidence, weight))
                break
    return rows


def compute_artifact_topic_rows(db: DevRefDatabase, topics: list[TopicDefinition]) -> list[tuple[int, str, str, str, str, float]]:
    """Recompute all artifact-topic link rows from current artifacts."""

    topic_ids = {topic.topic_id for topic in topics}
    rows: list[tuple[int, str, str, str, str, float]] = []
    artifact_rows = db.load_rows(
        """
        SELECT artifact_id, title, kind, facet, relation, summary, content, source_path, qualified_name, metadata_json
        FROM artifacts
        ORDER BY artifact_id
        """
    )
    for artifact in artifact_rows:
        metadata = json.loads(artifact["metadata_json"])
        annotations = [
            TopicAnnotation.model_validate(item)
            for item in metadata.get("annotations", [])
        ]
        rows.extend(
            _annotation_links(
                artifact["artifact_id"],
                annotations,
                artifact["facet"],
                artifact["relation"],
                topic_ids,
            )
        )
        rows.extend(
            _symbol_links(
                artifact["artifact_id"],
                list(metadata.get("symbol_refs", [])),
                artifact["facet"],
                artifact["relation"],
                topics,
            )
        )
        rows.extend(
            _heuristic_links(
                artifact["artifact_id"],
                artifact["title"],
                artifact["summary"],
                artifact["content"],
                artifact["source_path"],
                artifact["qualified_name"],
                artifact["kind"],
                artifact["facet"],
                artifact["relation"],
                topics,
            )
        )
    deduped: dict[tuple[int, str, str, str, str], float] = {}
    for artifact_id, topic_id, facet, relation, evidence_source, weight in rows:
        key = (artifact_id, topic_id, facet, relation, evidence_source)
        deduped[key] = max(weight, deduped.get(key, 0.0))
    return [
        (artifact_id, topic_id, facet, relation, evidence_source, weight)
        for (artifact_id, topic_id, facet, relation, evidence_source), weight in sorted(deduped.items())
    ]


def compute_artifact_link_rows(db: DevRefDatabase) -> list[tuple[int, int, str]]:
    """Rebuild cross-artifact links from current artifact metadata."""

    artifact_rows = db.load_rows(
        """
        SELECT artifact_id, source_path, qualified_name, metadata_json
        FROM artifacts
        ORDER BY artifact_id
        """
    )
    first_artifact_by_path: dict[str, int] = {}
    symbol_artifact_by_qname: dict[str, int] = {}
    for row in artifact_rows:
        first_artifact_by_path.setdefault(row["source_path"], row["artifact_id"])
        if row["qualified_name"]:
            symbol_artifact_by_qname[row["qualified_name"]] = row["artifact_id"]

    links: set[tuple[int, int, str]] = set()
    for row in artifact_rows:
        metadata = json.loads(row["metadata_json"])
        for related_path in metadata.get("related_paths", []):
            target_id = first_artifact_by_path.get(related_path)
            if target_id is not None:
                links.add((row["artifact_id"], target_id, "related_doc"))
        for qualified_name in metadata.get("symbol_refs", []):
            target_id = symbol_artifact_by_qname.get(qualified_name)
            if target_id is not None and target_id != row["artifact_id"]:
                links.add((row["artifact_id"], target_id, "references_symbol"))
    return sorted(links)


def _count_source_sets(previous: dict[str, str], current: dict[str, str]) -> tuple[list[str], list[str], list[str]]:
    previous_keys = set(previous)
    current_keys = set(current)
    removed = sorted(previous_keys - current_keys)
    changed = sorted(
        path for path in current_keys
        if previous.get(path) != current[path]
    )
    unchanged = sorted(current_keys - set(changed))
    return changed, removed, unchanged


def build_index(
    *,
    repo_root: str | Path | None = None,
    db_path: str | Path | None = None,
    incremental: bool = True,
    live_imports: bool = False,
) -> BuildReport:
    """Build or refresh the developer topic reference SQLite index."""

    repo_root_path = Path(repo_root) if repo_root is not None else REPO_ROOT
    db_file = Path(db_path) if db_path is not None else DEFAULT_DB_PATH
    db = DevRefDatabase(db_file)
    db.ensure_schema()

    topics = load_topics()
    registry_payload = topic_registry_hash()
    db.upsert_topics(topics, normalize_alias=normalize_text)

    source_paths = iter_source_paths(repo_root_path)
    manifest = {path.relative_to(repo_root_path).as_posix(): file_hash(path) for path in source_paths}
    meta = db.get_meta()
    previous_manifest = json.loads(meta.get("source_manifest_json", "{}"))
    requires_full = (
        not incremental
        or meta.get("builder_version") != BUILDER_VERSION
        or meta.get("topic_registry_payload") != registry_payload
        or not db_file.exists()
        or not previous_manifest
    )

    build_mode = "full"
    changed_paths: list[str]
    removed_paths: list[str]
    if requires_full:
        db.clear_dynamic_tables()
        db.ensure_schema()
        db.upsert_topics(topics, normalize_alias=normalize_text)
        changed_paths = sorted(manifest)
        removed_paths = []
    else:
        changed_paths, removed_paths, _ = _count_source_sets(previous_manifest, manifest)
        if not changed_paths and not removed_paths:
            used_fts = bool(meta.get("used_fts") == "1")
            return BuildReport(
                db_path=str(db_file),
                build_mode="noop",
                indexed_sources=len(source_paths),
                changed_sources=0,
                removed_sources=0,
                artifacts=db.artifact_count(),
                symbols=db.symbol_count(),
                topic_links=db.topic_link_count(),
                artifact_links=db.artifact_link_count(),
                used_fts=used_fts,
            )
        build_mode = "incremental"
        db.delete_source_paths(tuple(sorted(set(changed_paths + removed_paths))))

    extracted_artifacts: list[ExtractedArtifact] = []
    extracted_symbols: list[ExtractedSymbol] = []
    source_lookup = {path.relative_to(repo_root_path).as_posix(): path for path in source_paths}
    for source_key in changed_paths:
        path = source_lookup[source_key]
        artifacts, symbols = extract_source_file(
            path,
            manifest[source_key],
            repo_root_path,
            live_imports=live_imports,
        )
        extracted_artifacts.extend(artifacts)
        extracted_symbols.extend(symbols)

    db.insert_symbols(extracted_symbols)
    db.insert_artifacts(extracted_artifacts)

    topic_rows = compute_artifact_topic_rows(db, topics)
    db.replace_artifact_topics(topic_rows)

    link_rows = compute_artifact_link_rows(db)
    db.replace_artifact_links(link_rows)

    used_fts = db.replace_fts()
    db.set_meta(
        builder_version=BUILDER_VERSION,
        built_at=datetime.now(UTC).isoformat(),
        topic_registry_payload=registry_payload,
        source_manifest_json=json.dumps(manifest, sort_keys=True),
        used_fts="1" if used_fts else "0",
    )
    return BuildReport(
        db_path=str(db_file),
        build_mode=build_mode,
        indexed_sources=len(source_paths),
        changed_sources=len(changed_paths),
        removed_sources=len(removed_paths),
        artifacts=db.artifact_count(),
        symbols=db.symbol_count(),
        topic_links=db.topic_link_count(),
        artifact_links=db.artifact_link_count(),
        used_fts=used_fts,
    )
