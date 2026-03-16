from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any

from tangl.loaders.codec import DecodeResult, LossKind, LossRecord, SourceRef

if TYPE_CHECKING:
    from tangl.loaders.bundle import WorldBundle

FEATURE_LINK_SETTERS = "links:setters"
FEATURE_MACROS_IF = "macros:if"
FEATURE_MACROS_SET = "macros:set"
FEATURE_MACROS_PRINT = "macros:print"
FEATURE_MACROS_DISPLAY = "macros:display"
FEATURE_MACROS_DISPLAY_SHORT = "macros:display_shorthand"
FEATURE_MACROS_UNKNOWN = "macros:unknown"
FEATURE_SPECIAL_PASSAGE = "passages:special"
ISSUE_DANGLING_LINK = "source:dangling_link"
ISSUE_DUPLICATE_PASSAGE = "source:duplicate_passage"
ISSUE_INVALID_START = "source:invalid_start"
ISSUE_INVALID_STORY_DATA = "source:story_data_invalid"
ISSUE_SLUG_COLLISION = "source:slug_collision"

_HEADER_RE = re.compile(
    r"^::\s*(?P<name>[^\[{\n]+?)"
    r"(?:[ \t]+\[(?P<tags>[^\]]*)\])?"
    r"(?:[ \t]+(?P<meta>\{.*\}))?[ \t]*$",
    re.MULTILINE,
)
_LINK_RE = re.compile(
    r"\[\["
    r"(?:(?P<text>[^\]|>\[]+?)(?:\||->))?"
    r"(?P<target>[^\]\[]+?)"
    r"(?:\]\[(?P<setter_inner>[^\]]*))?"
    r"\]\]"
    r"(?:\[(?P<setter_outer>[^\]]*)\])?",
    re.DOTALL,
)
_MACRO_RE = re.compile(r"<<.+?>>", re.DOTALL)
_IF_BLOCK_RE = re.compile(
    r"<<\s*if\b(?P<condition>.*?)>>(?P<body>.*?)<<\s*endif\s*>>",
    re.DOTALL | re.IGNORECASE,
)
_IF_BRANCH_RE = re.compile(
    r"<<\s*(?P<kind>elseif|else)\b(?P<expr>.*?)>>",
    re.DOTALL | re.IGNORECASE,
)
_SET_MACRO_RE = re.compile(r"<<\s*set\b(?P<body>.*?)>>", re.DOTALL | re.IGNORECASE)
_VAR_RE = re.compile(r"\$([A-Za-z_]\w*)")
_CONSUMED_SPECIAL_PASSAGES = frozenset({"StoryTitle", "StoryData"})
_UNSUPPORTED_SPECIAL_PASSAGES = frozenset(
    {
        "StoryAuthor",
        "StoryBanner",
        "StoryCaption",
        "StoryInit",
        "StoryInterface",
        "StoryMenu",
        "StorySettings",
        "StoryShare",
        "StoryStylesheet",
        "StorySubtitle",
        "StoryScript",
        "PassageDone",
        "PassageFooter",
        "PassageHeader",
        "PassageReady",
    }
)


@dataclass(slots=True, frozen=True)
class RawPassage:
    """Parsed Twee passage before StoryTangl mapping."""

    name: str
    tags: list[str]
    meta: dict[str, Any]
    body: str
    path: str
    ordinal: int


@dataclass(slots=True, frozen=True)
class StoryMetadata:
    """Metadata extracted from special Twee passages."""

    title: str | None
    start_name: str | None
    story_format: str | None
    story_format_version: str | None


@dataclass(slots=True, frozen=True)
class IfBranch:
    """One branch from a simple Twine ``if`` / ``elseif`` / ``else`` block."""

    condition: str | None
    body: str


class TwineCodec:
    """Decode a small Twee 3 subset into StoryTangl near-native story data."""

    codec_id = "twee3_1_0"

    def decode(
        self,
        *,
        bundle: "WorldBundle",
        script_paths: list[Path],
        story_key: str | None,
    ) -> DecodeResult:
        refs = [
            SourceRef(path=str(script_path), story_key=story_key)
            for script_path in script_paths
        ]

        parsed_passages: list[RawPassage] = []
        ordinal = 0
        for script_path in script_paths:
            source = script_path.read_text(encoding="utf-8")
            passages = _parse_twee(source=source, path=script_path, start_ordinal=ordinal)
            parsed_passages.extend(passages)
            ordinal += len(passages)

        warnings: list[str] = []
        loss_records: list[LossRecord] = []

        merged_passages, merge_losses = _merge_passages(parsed_passages)
        loss_records.extend(merge_losses)

        metadata, metadata_losses = _extract_story_metadata(merged_passages)
        loss_records.extend(metadata_losses)

        content_passages: list[RawPassage] = []
        for passage in merged_passages:
            if passage.name in _CONSUMED_SPECIAL_PASSAGES:
                continue
            if _is_special_passage(passage.name):
                loss_records.append(
                    LossRecord(
                        kind=LossKind.UNSUPPORTED_FEATURE,
                        feature=FEATURE_SPECIAL_PASSAGE,
                        passage=passage.name,
                        excerpt=_trim_excerpt(passage.name),
                        note="Special passages outside StoryTitle and StoryData are ignored in v1.",
                    )
                )
                continue
            content_passages.append(passage)

        slug_map, slug_losses = _assign_slugs(content_passages)
        loss_records.extend(slug_losses)

        blocks: dict[str, dict[str, Any]] = {}
        used_labels = set(slug_map.values())
        start_passage_name = metadata.start_name or (content_passages[0].name if content_passages else None)
        seeded_story_locals: dict[str, Any] = {}
        passage_state: list[dict[str, Any]] = []
        for passage in content_passages:
            slug = slug_map[passage.name]
            content, actions, generated_blocks, effects, body_losses = _process_passage_body(
                passage=passage,
                slug_map=slug_map,
                used_labels=used_labels,
            )
            loss_records.extend(body_losses)
            block_data: dict[str, Any] = {
                "content": content,
                "actions": actions,
            }
            if effects:
                block_data["effects"] = effects
                if passage.name == start_passage_name:
                    _seed_story_locals_from_effects(story_locals=seeded_story_locals, effects=effects)
            if passage.tags:
                block_data["tags"] = list(passage.tags)
            blocks[slug] = block_data
            blocks.update(generated_blocks)
            passage_state.append(
                {
                    "name": passage.name,
                    "slug": slug,
                    "path": passage.path,
                    "ordinal": passage.ordinal,
                    "tags": list(passage.tags),
                    "meta": dict(passage.meta),
                }
            )

        default_title = bundle.manifest.story_label(story_key)
        metadata_dict: dict[str, Any] = {
            "title": metadata.title or default_title,
        }

        if blocks:
            start_slug = None
            if metadata.start_name is not None:
                start_slug = slug_map.get(metadata.start_name)
                if start_slug is None:
                    loss_records.append(
                        LossRecord(
                            kind=LossKind.SOURCE_INTEGRITY,
                            feature=ISSUE_INVALID_START,
                            passage="StoryData",
                            excerpt=_trim_excerpt(metadata.start_name),
                            note="Fell back to the first surviving passage.",
                        )
                    )
            if start_slug is None:
                start_slug = next(iter(blocks))
            metadata_dict["start_at"] = f"world.{start_slug}"
        else:
            warnings.append("Twine codec decoded no content passages.")

        if loss_records:
            warnings.append(
                f"Codec recorded {len(loss_records)} decode loss records; "
                "inspect codec_state['loss_records'] for structured details."
            )

        story_data = {
            "label": bundle.manifest.story_label(story_key),
            "metadata": metadata_dict,
            "scenes": {
                "world": {
                    "blocks": blocks,
                }
            },
        }
        if seeded_story_locals:
            story_data["globals"] = dict(seeded_story_locals)

        return DecodeResult(
            story_data=story_data,
            source_map={"__source_files__": refs},
            codec_state={
                "codec_id": self.codec_id,
                "codec_version": "1.0",
                "script_paths": [str(path) for path in script_paths],
                "story_key": story_key,
                "world_label": bundle.manifest.label,
                "story_format": metadata.story_format,
                "story_format_version": metadata.story_format_version,
                "passage_count": len(content_passages),
                "generated_block_count": max(len(blocks) - len(content_passages), 0),
                "passages": passage_state,
            },
            warnings=warnings,
            loss_records=loss_records,
        )

    def encode(
        self,
        *,
        bundle: "WorldBundle",
        runtime_data: dict[str, Any],
        story_key: str | None,
        codec_state: dict[str, Any] | None = None,
    ) -> dict[str, str]:
        _ = bundle, runtime_data, story_key, codec_state
        raise NotImplementedError(
            "TwineCodec.encode() is not supported in v1; this codec is decode-only."
        )


def _parse_twee(*, source: str, path: Path, start_ordinal: int) -> list[RawPassage]:
    matches = list(_HEADER_RE.finditer(source))
    if not matches:
        return []

    passages: list[RawPassage] = []
    for index, match in enumerate(matches):
        body_start = match.end()
        body_end = matches[index + 1].start() if index + 1 < len(matches) else len(source)
        body = source[body_start:body_end].strip()

        tags_raw = (match.group("tags") or "").strip()
        tags = [tag for tag in tags_raw.split() if tag]
        meta = _parse_header_meta(match.group("meta"))

        passages.append(
            RawPassage(
                name=match.group("name").strip(),
                tags=tags,
                meta=meta,
                body=body,
                path=str(path),
                ordinal=start_ordinal + index,
            )
        )

    return passages


def _parse_header_meta(raw_meta: str | None) -> dict[str, Any]:
    if not raw_meta:
        return {}

    try:
        parsed = json.loads(raw_meta)
    except json.JSONDecodeError:
        return {}

    return parsed if isinstance(parsed, dict) else {}


def _merge_passages(passages: list[RawPassage]) -> tuple[list[RawPassage], list[LossRecord]]:
    ordered: dict[str, RawPassage] = {}
    loss_records: list[LossRecord] = []

    for passage in passages:
        prior = ordered.pop(passage.name, None)
        if prior is not None:
            loss_records.append(
                LossRecord(
                    kind=LossKind.SOURCE_INTEGRITY,
                    feature=ISSUE_DUPLICATE_PASSAGE,
                    passage=passage.name,
                    excerpt=_trim_excerpt(passage.name),
                    note=f"{passage.path} overwrote {prior.path}.",
                )
            )
        ordered[passage.name] = passage

    return list(ordered.values()), loss_records


def _extract_story_metadata(passages: list[RawPassage]) -> tuple[StoryMetadata, list[LossRecord]]:
    title: str | None = None
    start_name: str | None = None
    story_format: str | None = None
    story_format_version: str | None = None
    loss_records: list[LossRecord] = []

    for passage in passages:
        if passage.name == "StoryTitle":
            title = passage.body.strip() or title
            continue
        if passage.name != "StoryData":
            continue

        try:
            data = json.loads(passage.body or "{}")
        except json.JSONDecodeError:
            data = None

        if not isinstance(data, dict):
            loss_records.append(
                LossRecord(
                    kind=LossKind.SOURCE_INTEGRITY,
                    feature=ISSUE_INVALID_STORY_DATA,
                    passage=passage.name,
                    excerpt=_trim_excerpt(passage.body),
                    note="StoryData must contain a JSON object.",
                )
            )
            continue

        if title is None:
            raw_title = data.get("name")
            if isinstance(raw_title, str) and raw_title.strip():
                title = raw_title.strip()
        raw_start = data.get("start")
        if isinstance(raw_start, str) and raw_start.strip():
            start_name = raw_start.strip()
        raw_format = data.get("format")
        if isinstance(raw_format, str) and raw_format.strip():
            story_format = raw_format.strip()
        raw_version = data.get("format-version")
        if isinstance(raw_version, str) and raw_version.strip():
            story_format_version = raw_version.strip()

    return (
        StoryMetadata(
            title=title,
            start_name=start_name,
            story_format=story_format,
            story_format_version=story_format_version,
        ),
        loss_records,
    )


def _assign_slugs(passages: list[RawPassage]) -> tuple[dict[str, str], list[LossRecord]]:
    slug_map: dict[str, str] = {}
    base_counts: dict[str, int] = {}
    loss_records: list[LossRecord] = []

    for passage in passages:
        base_slug = _slugify(passage.name)
        count = base_counts.get(base_slug, 0)
        if count == 0:
            slug = base_slug
        else:
            slug = f"{base_slug}_{count + 1}"
            loss_records.append(
                LossRecord(
                    kind=LossKind.SOURCE_INTEGRITY,
                    feature=ISSUE_SLUG_COLLISION,
                    passage=passage.name,
                    excerpt=_trim_excerpt(passage.name),
                    note=f"Normalized slug {base_slug!r} collided with another surviving passage.",
                )
            )
        base_counts[base_slug] = count + 1
        slug_map[passage.name] = slug

    return slug_map, loss_records


def _process_passage_body(
    *,
    passage: RawPassage,
    slug_map: dict[str, str],
    used_labels: set[str],
) -> tuple[str, list[dict[str, Any]], dict[str, dict[str, Any]], list[str], list[LossRecord]]:
    actions: list[dict[str, Any]] = []
    generated_blocks: dict[str, dict[str, Any]] = {}
    effects: list[str] = []
    loss_records: list[LossRecord] = []
    text, if_actions, if_blocks, if_losses = _lower_if_blocks(
        text=passage.body,
        passage=passage,
        slug_map=slug_map,
        used_labels=used_labels,
    )
    actions.extend(if_actions)
    generated_blocks.update(if_blocks)
    loss_records.extend(if_losses)

    text, set_effects, set_losses = _strip_supported_set_macros(
        text=text,
        passage_name=passage.name,
    )
    effects.extend(set_effects)
    loss_records.extend(set_losses)

    text, bare_actions, bare_blocks, bare_losses = _lower_links_in_text(
        text=text,
        passage=passage,
        slug_map=slug_map,
        used_labels=used_labels,
        condition_expr=None,
    )
    actions.extend(bare_actions)
    generated_blocks.update(bare_blocks)
    loss_records.extend(bare_losses)

    content, macro_losses = _strip_macros(
        text=text,
        passage_name=passage.name,
    )
    loss_records.extend(macro_losses)
    return content, actions, generated_blocks, effects, loss_records


def _lower_if_blocks(
    *,
    text: str,
    passage: RawPassage,
    slug_map: dict[str, str],
    used_labels: set[str],
) -> tuple[str, list[dict[str, Any]], dict[str, dict[str, Any]], list[LossRecord]]:
    actions: list[dict[str, Any]] = []
    generated_blocks: dict[str, dict[str, Any]] = {}
    loss_records: list[LossRecord] = []
    content_parts: list[str] = []
    cursor = 0

    for match in _IF_BLOCK_RE.finditer(text):
        content_parts.append(text[cursor:match.start()])
        branch_actions, branch_blocks, branch_losses = _lower_if_block_match(
            match=match,
            passage=passage,
            slug_map=slug_map,
            used_labels=used_labels,
        )
        actions.extend(branch_actions)
        generated_blocks.update(branch_blocks)
        loss_records.extend(branch_losses)
        cursor = match.end()

    content_parts.append(text[cursor:])
    return "".join(content_parts), actions, generated_blocks, loss_records


def _lower_if_block_match(
    *,
    match: re.Match[str],
    passage: RawPassage,
    slug_map: dict[str, str],
    used_labels: set[str],
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]], list[LossRecord]]:
    raw_condition = (match.group("condition") or "").strip()
    body = match.group("body") or ""
    loss_records: list[LossRecord] = []

    branches = _parse_if_branches(raw_condition=raw_condition, body=body)
    if branches is None:
        return [], {}, [_unsupported_if_loss(passage_name=passage.name, excerpt=match.group(0))]

    prior_conditions: list[str] = []
    actions: list[dict[str, Any]] = []
    generated_blocks: dict[str, dict[str, Any]] = {}

    for branch in branches:
        branch_condition, condition_losses = _lower_if_branch_condition(
            branch=branch,
            prior_conditions=prior_conditions,
            passage_name=passage.name,
        )
        if condition_losses:
            loss_records.extend(condition_losses)
            return [], {}, loss_records

        branch_text = branch.body.strip()
        if not branch_text:
            continue
        if _MACRO_RE.search(branch_text):
            return [], {}, [_unsupported_if_loss(passage_name=passage.name, excerpt=match.group(0))]

        lowered_text, branch_actions, branch_blocks, branch_losses = _lower_links_in_text(
            text=branch_text,
            passage=passage,
            slug_map=slug_map,
            used_labels=used_labels,
            condition_expr=branch_condition,
            require_links_only=True,
        )
        if lowered_text.strip():
            return [], {}, [_unsupported_if_loss(passage_name=passage.name, excerpt=match.group(0))]
        actions.extend(branch_actions)
        generated_blocks.update(branch_blocks)
        loss_records.extend(branch_losses)

        if branch.condition is not None:
            translated_condition = _translate_twine_expression(branch.condition)
            if translated_condition is not None:
                prior_conditions.append(translated_condition)

    return actions, generated_blocks, loss_records


def _parse_if_branches(*, raw_condition: str, body: str) -> list[IfBranch] | None:
    if not raw_condition:
        return None

    branches: list[IfBranch] = []
    cursor = 0
    current_condition: str | None = raw_condition
    saw_else = False

    for match in _IF_BRANCH_RE.finditer(body):
        kind = (match.group("kind") or "").strip().lower()
        branches.append(IfBranch(condition=current_condition, body=body[cursor:match.start()]))
        if kind == "elseif":
            if saw_else:
                return None
            current_condition = (match.group("expr") or "").strip()
            if not current_condition:
                return None
        elif kind == "else":
            if saw_else:
                return None
            saw_else = True
            current_condition = None
        else:  # pragma: no cover - defensive
            return None
        cursor = match.end()

    branches.append(IfBranch(condition=current_condition, body=body[cursor:]))
    return branches


def _lower_if_branch_condition(
    *,
    branch: IfBranch,
    prior_conditions: list[str],
    passage_name: str,
) -> tuple[str | None, list[LossRecord]]:
    translated_current: str | None = None
    if branch.condition is not None:
        translated_current = _translate_twine_expression(branch.condition)
        if translated_current is None:
            return None, [_unsupported_if_loss(passage_name=passage_name, excerpt=branch.condition)]

    combined: list[str] = [f"not ({condition})" for condition in prior_conditions]
    if translated_current is not None:
        combined.append(f"({translated_current})")
    if not combined:
        return None, []
    return " and ".join(combined), []


def _lower_links_in_text(
    *,
    text: str,
    passage: RawPassage,
    slug_map: dict[str, str],
    used_labels: set[str],
    condition_expr: str | None,
    require_links_only: bool = False,
) -> tuple[str, list[dict[str, Any]], dict[str, dict[str, Any]], list[LossRecord]]:
    actions: list[dict[str, Any]] = []
    generated_blocks: dict[str, dict[str, Any]] = {}
    loss_records: list[LossRecord] = []
    content_parts: list[str] = []
    cursor = 0

    for index, match in enumerate(_LINK_RE.finditer(text), start=1):
        content_parts.append(text[cursor:match.start()])
        link_action, generated_block, link_losses = _lower_link_match(
            match=match,
            passage=passage,
            slug_map=slug_map,
            used_labels=used_labels,
            link_index=index,
            condition_expr=condition_expr,
        )
        if link_action is not None:
            actions.append(link_action)
        if generated_block is not None:
            generated_blocks[generated_block["label"]] = generated_block
        loss_records.extend(link_losses)
        cursor = match.end()

    content_parts.append(text[cursor:])
    lowered_text = "".join(content_parts)
    if require_links_only and lowered_text.strip():
        return lowered_text, [], {}, loss_records
    return lowered_text, actions, generated_blocks, loss_records


def _lower_link_match(
    *,
    match: re.Match[str],
    passage: RawPassage,
    slug_map: dict[str, str],
    used_labels: set[str],
    link_index: int,
    condition_expr: str | None,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None, list[LossRecord]]:
    link_text = (match.group("text") or match.group("target") or "").strip()
    target_name = (match.group("target") or "").strip()
    setter = (match.group("setter_inner") or match.group("setter_outer") or "").strip()
    loss_records: list[LossRecord] = []

    if not target_name:
        return None, None, loss_records

    successor_slug = slug_map.get(target_name)
    if successor_slug is None:
        successor_slug = _slugify(target_name)
        loss_records.append(
            LossRecord(
                kind=LossKind.AUTHORING_DEBT,
                feature=ISSUE_DANGLING_LINK,
                passage=passage.name,
                excerpt=_trim_excerpt(target_name),
                note="Target passage was not present in decoded sources.",
            )
        )

    effects: list[str] = []
    if setter:
        effects, setter_losses = _translate_twine_set_ops(
            raw=setter,
            passage_name=passage.name,
            feature=FEATURE_LINK_SETTERS,
        )
        loss_records.extend(setter_losses)

    action: dict[str, Any] = {
        "text": link_text or target_name,
    }
    if condition_expr or effects:
        generated_label = _reserve_generated_label(
            used_labels=used_labels,
            base=f"{_slugify(passage.name)}__link_{link_index}",
        )
        action["successor_ref"] = generated_label
        generated_block: dict[str, Any] = {
            "label": generated_label,
            "content": "",
            "continues": [
                {
                    "successor_ref": successor_slug,
                    "authored_successor_ref": target_name,
                    "trigger": "last",
                }
            ],
            "is_anonymous": True,
        }
        if condition_expr:
            generated_block["availability"] = [{"expr": condition_expr}]
        if effects:
            generated_block["effects"] = effects
        return action, generated_block, loss_records

    action["successor_ref"] = successor_slug
    action["authored_successor_ref"] = target_name
    return action, None, loss_records


def _strip_supported_set_macros(
    *,
    text: str,
    passage_name: str,
) -> tuple[str, list[str], list[LossRecord]]:
    effects: list[str] = []
    loss_records: list[LossRecord] = []
    content_parts: list[str] = []
    cursor = 0

    for match in _SET_MACRO_RE.finditer(text):
        content_parts.append(text[cursor:match.start()])
        translated_effects, set_losses = _translate_twine_set_ops(
            raw=match.group("body") or "",
            passage_name=passage_name,
            feature=FEATURE_MACROS_SET,
        )
        effects.extend(translated_effects)
        loss_records.extend(set_losses)
        cursor = match.end()

    content_parts.append(text[cursor:])
    return "".join(content_parts), effects, loss_records


def _translate_twine_set_ops(
    *,
    raw: str,
    passage_name: str,
    feature: str,
) -> tuple[list[str], list[LossRecord]]:
    statements = [
        statement.strip()
        for statement in re.split(r"[;\n]+", raw)
        if statement.strip()
    ]
    effects: list[str] = []
    loss_records: list[LossRecord] = []

    if not statements:
        loss_records.append(
            LossRecord(
                kind=LossKind.UNSUPPORTED_FEATURE,
                feature=feature,
                passage=passage_name,
                excerpt=_trim_excerpt(raw),
                note="Only simple variable assignment setters are supported.",
            )
        )
        return effects, loss_records

    assignment_re = re.compile(
        r"^\s*\$(?P<name>[A-Za-z_]\w*)\s*(?P<op>to|=|\+=|-=|\*=|/=)\s*(?P<rhs>.+?)\s*$",
        re.IGNORECASE,
    )

    for statement in statements:
        match = assignment_re.match(statement)
        if match is None:
            loss_records.append(
                LossRecord(
                    kind=LossKind.UNSUPPORTED_FEATURE,
                    feature=feature,
                    passage=passage_name,
                    excerpt=_trim_excerpt(statement),
                    note="Only simple variable assignment setters are supported.",
                )
            )
            continue

        rhs = _translate_twine_expression(match.group("rhs"))
        if rhs is None:
            loss_records.append(
                LossRecord(
                    kind=LossKind.UNSUPPORTED_FEATURE,
                    feature=feature,
                    passage=passage_name,
                    excerpt=_trim_excerpt(statement),
                    note="Setter expression could not be lowered safely.",
                )
            )
            continue

        name = match.group("name")
        op = match.group("op").lower()
        key_ref = f"self.graph.locals['{name}']"
        current_ref = f"self.graph.locals.get('{name}', 0)"
        if op in {"to", "="}:
            effects.append(f"{key_ref} = {rhs}")
        elif op == "+=":
            effects.append(f"{key_ref} = {current_ref} + ({rhs})")
        elif op == "-=":
            effects.append(f"{key_ref} = {current_ref} - ({rhs})")
        elif op == "*=":
            effects.append(f"{key_ref} = {current_ref} * ({rhs})")
        elif op == "/=":
            effects.append(f"{key_ref} = {current_ref} / ({rhs})")

    return effects, loss_records


def _translate_twine_expression(raw: str) -> str | None:
    expr = raw.strip()
    if not expr:
        return None

    if re.search(r"\b(contains|matches|to|into)\b", expr, flags=re.IGNORECASE):
        return None

    expr = _VAR_RE.sub(
        lambda match: f"self.graph.locals.get('{match.group(1)}')",
        expr,
    )

    replacements = (
        (r"\bis\s+not\b", "!="),
        (r"\bisnot\b", "!="),
        (r"\beq\b", "=="),
        (r"\bneq\b", "!="),
        (r"\bgte\b", ">="),
        (r"\blte\b", "<="),
        (r"\bgt\b", ">"),
        (r"\blt\b", "<"),
        (r"\bis\b", "=="),
        (r"\btrue\b", "True"),
        (r"\bfalse\b", "False"),
        (r"\bnull\b", "None"),
    )
    for pattern, replacement in replacements:
        expr = re.sub(pattern, replacement, expr, flags=re.IGNORECASE)

    return expr.strip() or None


def _reserve_generated_label(*, used_labels: set[str], base: str) -> str:
    label = base
    counter = 2
    while label in used_labels:
        label = f"{base}_{counter}"
        counter += 1
    used_labels.add(label)
    return label


def _unsupported_if_loss(*, passage_name: str, excerpt: str) -> LossRecord:
    return LossRecord(
        kind=LossKind.UNSUPPORTED_FEATURE,
        feature=FEATURE_MACROS_IF,
        passage=passage_name,
        excerpt=_trim_excerpt(excerpt),
        note="Only link-only if/elseif/else blocks are supported in this Twine import layer.",
    )


def _seed_story_locals_from_effects(*, story_locals: dict[str, Any], effects: list[str]) -> None:
    seed_self = SimpleNamespace(graph=SimpleNamespace(locals=story_locals))
    for effect in effects:
        exec(effect, {"__builtins__": {}}, {"self": seed_self})


def _strip_macros(*, text: str, passage_name: str) -> tuple[str, list[LossRecord]]:
    loss_records: list[LossRecord] = []
    content_parts: list[str] = []
    cursor = 0

    for match in _MACRO_RE.finditer(text):
        content_parts.append(text[cursor:match.start()])
        macro_text = match.group(0)
        loss_records.append(
            LossRecord(
                kind=LossKind.UNSUPPORTED_FEATURE,
                feature=_classify_macro(macro_text),
                passage=passage_name,
                excerpt=_trim_excerpt(macro_text),
                note="Macros are stripped during Twee v1 import.",
            )
        )
        cursor = match.end()

    content_parts.append(text[cursor:])
    return "".join(content_parts).strip(), loss_records


def _classify_macro(macro_text: str) -> str:
    inner = macro_text[2:-2].strip()
    if not inner:
        return FEATURE_MACROS_UNKNOWN

    keyword = inner.split()[0].lower()
    if keyword in {"if", "elseif", "else", "endif"}:
        return FEATURE_MACROS_IF
    if keyword == "set":
        return FEATURE_MACROS_SET
    if keyword == "print":
        return FEATURE_MACROS_PRINT
    if keyword in {"display", "include"}:
        return FEATURE_MACROS_DISPLAY
    if re.fullmatch(r"[A-Za-z_][\w-]*", keyword):
        return FEATURE_MACROS_DISPLAY_SHORT
    return FEATURE_MACROS_UNKNOWN


def _slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    normalized = normalized.lower().strip()
    normalized = re.sub(r"[^a-z0-9]+", "_", normalized)
    normalized = normalized.strip("_")
    return normalized or "passage"


def _is_special_passage(name: str) -> bool:
    return name.startswith("Story") or name in _UNSUPPORTED_SPECIAL_PASSAGES


def _trim_excerpt(value: str, *, limit: int = 120) -> str:
    excerpt = " ".join(value.split())
    if len(excerpt) <= limit:
        return excerpt
    return excerpt[: limit - 3] + "..."
