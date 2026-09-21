"""Executable comparison of neutral text annotation and adapter realization.

This is a diagnostic experiment, not a production fragment or rendering API.
It deliberately keeps its attributed-text candidate inside conformance output
until issues #457 and #454 settle the canonical value and persistence shape.
"""

from __future__ import annotations

import html
import io
import json
import re
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Mapping, cast

from tangl.journal.fragments import (
    AttributedFragment,
    ChoiceFragment,
    ContentFragment,
    GroupFragment,
    KvFragment,
    MediaFragment,
)
from tangl.presentation.events import UxEvent
from tangl.prose import render_text
from tangl.service.response import RuntimeEnvelope
from tangl.story.story_graph import StoryGraph
from tangl.vm.runtime.frame import PhaseCtx
from tangl.vm.traversable import TraversableNode


HERE = Path(__file__).parent
SOURCE_DIR = HERE / "diagnostics" / "presentation" / "authored"
REPORT_PATH = HERE / "diagnostics" / "presentation" / "realization_report.json"
SOURCE_PATHS = (
    SOURCE_DIR / "prose_dialog.json",
    SOURCE_DIR / "mixed_packet.json",
)

DEFAULT_TERMINAL_STYLES = {
    "block:admonition": "bold yellow",
    "fragment:dialog": "cyan",
    "group:status_packet": "blue",
    "inline:emphasis": "bold",
    "speaker:guide": "cyan",
    "state:locked": "dim",
    "tone:warning": "yellow",
    "ux:warning": "yellow",
}

FRAGMENT_MODELS = {
    "attributed": AttributedFragment,
    "choice": ChoiceFragment,
    "content": ContentFragment,
    "group": GroupFragment,
    "kv": KvFragment,
    "media": MediaFragment,
}

OFFSET_UNIT = "unicode_scalar_values"
PROJECTION_REALIZATION_MATRIX = {
    "dimensions": {
        "projection_resolution": "sampling density from episodic spine to visible surface",
        "realization_binding": "transport or renderer binding of the projected disclosure",
    },
    "durable_floor": [
        "stable fragment and action identity with provenance",
        "canonical replayable semantic or procedural packet",
        "offered action identity and current reachability",
        "type-defined fallback or unsupported-type diagnostic",
    ],
    "replay_contract": [
        "graph and causal replay restores the replayable semantic story state",
        "journal and projection replay walks the stored ordered record stream",
        "exact rendition replay is optional archival scope and is not currently promised",
    ],
    "authority_chain": [
        {
            "stage": "graph",
            "authority": "delta and checkpoint stack",
            "contract": "replayable semantic story state",
        },
        {
            "stage": "journal-phase",
            "authority": "backend projection function",
            "contract": (
                "deterministically realizes graph, cursor, concepts, namespace, and handlers"
            ),
        },
        {
            "stage": "journal-registry",
            "authority": "ordered linearized projection",
            "contract": "walking records recovers the fragment and event stream",
        },
        {
            "stage": "transport",
            "authority": "client packet projection",
            "contract": "packages journal records without defining final rendition",
        },
        {
            "stage": "client",
            "authority": "rendering and interaction presentation policy",
            "contract": "may omit, rearrange, enrich, or vocalize; actions remain backend-owned",
        },
    ],
    "client_boundaries": {
        "reference": "complete supported public vocabulary with documented fallback",
        "third_party": "may consume a strict subset or derive richer output",
        "prose_blind_bot": (
            "may ignore prose and media, consume current state and offered action identities, "
            "and submit through the normal action contract"
        ),
        "expanded_graph_access": (
            "admin, development, offline-analysis, or explicitly disclosed capability"
        ),
    },
    "points": [
        {
            "name": "typed-neutral-fragments",
            "projection_resolution": "middle",
            "realization_binding": "renderer-neutral typed JSON",
            "status": "supported floor",
            "cost_and_replay": "bounded identity count; causal and semantic replay",
        },
        {
            "name": "attributed-neutral-text",
            "projection_resolution": "fine",
            "realization_binding": "text plus explicit annotation spans",
            "status": "experimental refinement",
            "cost_and_replay": "more boundaries and validation; deterministic and replayable",
        },
        {
            "name": "derived-structural-html-rich",
            "projection_resolution": "fine to tessellated",
            "realization_binding": "classed HTML or adapter-local Rich primitives",
            "status": "supported derivation",
            "cost_and_replay": "consumer work; exact historical rendition is not promised",
        },
        {
            "name": "client-generated-from-coarse-gloss",
            "projection_resolution": "coarse",
            "realization_binding": "nondeterministic client refinement",
            "status": "valid ephemeral realization of a stored typed packet",
            "cost_and_replay": (
                "low backend sampling; semantic replay without exact rendition replay"
            ),
        },
    ],
    "bundle_positions": {
        "prose-dialog": ["typed-neutral-fragments", "attributed-neutral-text"],
        "mixed-packet": ["typed-neutral-fragments"],
    },
}
_BLOCK_MARKUP = re.compile(
    r"\A:::\s+\{(?P<attributes>[^{}\n]+)\}\n(?P<body>.*)\n:::\Z",
    re.DOTALL,
)
_INLINE_MARKUP = re.compile(
    r"\[(?P<text>[^\[\]]*)\]\{(?P<attributes>\.[^{}]+)\}",
)


class _ReadableHtml(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def safe_class_token(token: str) -> str:
    """Encode one advisory token as an injective, selector-safe class name."""

    return f"st-x{token.encode('utf-8').hex()}"


def _render_template(template: str, namespace: dict[str, object]) -> str:
    if not template or not template.strip():
        return template
    graph = StoryGraph(locals=namespace)
    cursor = TraversableNode(label="presentation-realization-diagnostic")
    graph.add(cursor)
    ctx = PhaseCtx(graph=graph, cursor_id=cursor.uid)
    leading = re.match(r"^\s*", template).group()
    trailing = re.search(r"\s*$", template).group()
    rendered = render_text(template.strip(), ctx=ctx, source=cursor)
    if not rendered:
        return ""
    return f"{leading}{rendered}{trailing}"


def _validate_scalar_text(text: str) -> None:
    if any(0xD800 <= ord(character) <= 0xDFFF for character in text):
        raise ValueError("Attributed text offsets require Unicode scalar values")


def _plain_text_candidate(text: str) -> dict[str, object]:
    _validate_scalar_text(text)
    return {"text": text, "spans": [], "offset_unit": OFFSET_UNIT}


def _class_tokens(attributes: str) -> list[str]:
    parts = attributes.split()
    if not parts or any(not part.startswith(".") or len(part) == 1 for part in parts):
        raise ValueError("The diagnostic Pandoc-like grammar accepts classes only")
    return [part[1:] for part in parts]


def parse_pandoc_markup(
    markup: str,
    namespace: dict[str, object],
) -> tuple[dict[str, object], dict[str, object]]:
    """Evaluate and parse the diagnostic's deliberately flat Pandoc-like subset."""

    evaluated = _render_template(markup, namespace)
    block = _BLOCK_MARKUP.fullmatch(evaluated)
    if block is None:
        raise ValueError("Expected one Pandoc-like classed block")

    body = block.group("body")
    text_parts: list[str] = []
    spans: list[dict[str, object]] = []
    cursor = 0
    text_length = 0
    while cursor < len(body):
        open_index = body.find("[", cursor)
        if open_index < 0:
            tail = body[cursor:]
            text_parts.append(tail)
            text_length += len(tail)
            break
        prefix = body[cursor:open_index]
        text_parts.append(prefix)
        text_length += len(prefix)
        inline = _INLINE_MARKUP.match(body, open_index)
        if inline is None:
            raise ValueError("Nested, overlapping, or unclassed spans are not supported")
        span_text = inline.group("text")
        _validate_scalar_text(span_text)
        start = text_length
        text_parts.append(span_text)
        text_length += len(span_text)
        spans.append(
            {
                "start": start,
                "end": text_length,
                "tokens": _class_tokens(inline.group("attributes")),
            }
        )
        cursor = inline.end()

    text = "".join(text_parts)
    _validate_scalar_text(text)
    neutral = {"text": text, "spans": spans, "offset_unit": OFFSET_UNIT}
    trace = {
        "source_format": "pandoc-like",
        "evaluated_markup": evaluated,
        "block_tokens": _class_tokens(block.group("attributes")),
        "neutral_text": neutral,
    }
    return neutral, trace


def adapt_authored_bundle(
    source: Mapping[str, object],
) -> tuple[dict[str, object], dict[str, object]]:
    """Evaluate authored syntax and expose the authoring-adapter boundary."""

    namespace = dict(cast(Mapping[str, object], source.get("context", {})))
    fragments = []
    fragment_traces = []
    for source_fragment in cast(list[dict[str, object]], source["fragments"]):
        payload = dict(source_fragment)
        fragment_type = str(payload["fragment_type"])
        trace: dict[str, object] = {
            "uid": payload["uid"],
            "fragment_type": fragment_type,
        }
        authored_markup = payload.pop("authored_markup", None)
        authored_template = payload.pop("authored_template", None)
        if authored_markup is not None:
            normalized_text, markup_trace = parse_pandoc_markup(
                str(authored_markup),
                namespace,
            )
            trace.update(markup_trace)
            hints = dict(cast(Mapping[str, object], payload.get("hints", {})))
            hints["style_tags"] = [
                *cast(list[str], hints.get("style_tags", [])),
                *cast(list[str], markup_trace["block_tokens"]),
            ]
            payload["hints"] = hints
            payload["content"] = normalized_text
        elif authored_template is not None:
            rendered = _render_template(str(authored_template), namespace)
            normalized_text = _plain_text_candidate(rendered)
            trace["evaluated_template"] = rendered
            trace["neutral_text"] = normalized_text
            if fragment_type == "choice":
                payload["text"] = rendered
            else:
                payload["content"] = normalized_text

        if fragment_type == "kv":
            rows = []
            for source_row in cast(list[dict[str, object]], payload.pop("authored_rows")):
                row = dict(source_row)
                row["value"] = _render_template(str(row.pop("value_template")), namespace)
                rows.append(row)
            payload["content"] = rows
            trace["evaluated_rows"] = rows

        fallback_template = payload.pop("fallback_template", None)
        if fallback_template is not None:
            payload["fallback_text"] = _render_template(
                str(fallback_template),
                namespace,
            )
            trace["evaluated_fallback"] = payload["fallback_text"]

        model = FRAGMENT_MODELS[fragment_type]
        fragments.append(model.model_validate(payload))
        fragment_traces.append(trace)

    ux_events = []
    event_traces = []
    for source_event in cast(list[dict[str, object]], source.get("ux_events", [])):
        payload = dict(source_event)
        payload["message"] = _render_template(str(payload.pop("message_template")), namespace)
        ux_events.append(UxEvent.model_validate(payload))
        event_traces.append(
            {"event_id": payload["event_id"], "evaluated_message": payload["message"]}
        )

    envelope = RuntimeEnvelope(
        fragments=fragments,
        ux_events=ux_events,
        metadata={"diagnostic_bundle": source["bundle_id"]},
    )
    return envelope.to_dto(), {
        "fragments": fragment_traces,
        "ux_events": event_traces,
        "offset_unit": OFFSET_UNIT,
        "span_policy": "flat, non-overlapping, adjacent allowed",
    }


def normalize_bundle(source: Mapping[str, object]) -> dict[str, object]:
    """Return the experimental neutral DTO after authoring adaptation."""

    return adapt_authored_bundle(source)[0]


def _text_value(value: object) -> str:
    if isinstance(value, Mapping):
        return str(value.get("text", ""))
    return str(value or "")


def readable_text(dto: Mapping[str, object]) -> str:
    """Return the complete text-floor reading of one normalized bundle."""

    lines: list[str] = []
    for fragment in cast(list[dict[str, object]], dto["fragments"]):
        fragment_type = fragment["fragment_type"]
        if fragment_type == "content":
            lines.append(_text_value(fragment.get("content")))
        elif fragment_type == "attributed":
            how = f" ({fragment['how']})" if fragment.get("how") else ""
            lines.append(
                f"{str(fragment['who']).upper()}{how}: "
                f"{_text_value(fragment.get('content'))}"
            )
        elif fragment_type == "kv":
            for row in cast(list[dict[str, object]], fragment.get("content", [])):
                lines.append(f"{row['key']}: {row['value']}")
        elif fragment_type == "choice":
            marker = "1" if fragment.get("available", True) else "x"
            reason = (
                f" [locked: {fragment['unavailable_reason']}]"
                if fragment.get("unavailable_reason")
                else ""
            )
            lines.append(f"{marker}) {fragment['text']}{reason}")
        elif fragment_type == "media":
            role = fragment.get("media_role") or "media"
            fallback = fragment.get("fallback_text") or fragment.get("content")
            lines.append(f"[{role}: {fallback}]")

    for event in cast(list[dict[str, object]], dto.get("ux_events", [])):
        lines.append(f"[{event['severity']}] {event['message']}")
    return "\n".join(lines)


def _style_tags(fragment: Mapping[str, object]) -> list[str]:
    hints = fragment.get("hints") or fragment.get("presentation_hints")
    if not isinstance(hints, Mapping):
        return []
    return [str(value) for value in hints.get("style_tags", [])]


def _text_runs(fragment: Mapping[str, object]) -> list[dict[str, object]]:
    content = fragment.get("content")
    if isinstance(content, Mapping) and isinstance(content.get("spans"), list):
        if content.get("offset_unit") != OFFSET_UNIT:
            raise ValueError(f"Expected {OFFSET_UNIT} attributed-text offsets")
        text = str(content.get("text", ""))
        runs: list[dict[str, object]] = []
        cursor = 0
        for span in cast(list[dict[str, object]], content["spans"]):
            start = int(span["start"])
            end = int(span["end"])
            if start < cursor or end <= start or end > len(text):
                raise ValueError("Attributed text spans must be flat and non-overlapping")
            if start > cursor:
                runs.append({"text": text[cursor:start], "classes": []})
            runs.append(
                {
                    "text": text[start:end],
                    "classes": [str(value) for value in span.get("tokens", [])],
                }
            )
            cursor = end
        if cursor < len(text):
            runs.append({"text": text[cursor:], "classes": []})
        return runs
    return [{"text": _text_value(content), "classes": []}]


def _class_attribute(tokens: list[str]) -> str:
    if not tokens:
        return ""
    classes = " ".join(safe_class_token(token) for token in tokens)
    return f' class="{classes}"'


def _html_runs(fragment: Mapping[str, object]) -> str:
    output = []
    for run in _text_runs(fragment):
        text = html.escape(str(run["text"]))
        classes = [str(value) for value in run.get("classes", [])]
        if classes:
            output.append(f"<span{_class_attribute(classes)}>{text}</span>")
        else:
            output.append(text)
    return "".join(output)


def _data_attributes(fragment: Mapping[str, object]) -> str:
    pairs = [("fragment-id", fragment.get("uid"))]
    for name in ("origin_id", "source_id"):
        if fragment.get(name) is not None:
            pairs.append((name.replace("_", "-"), fragment[name]))
    return "".join(
        f' data-{name}="{html.escape(str(value), quote=True)}"'
        for name, value in pairs
        if value is not None
    )


def realize_html(dto: Mapping[str, object]) -> dict[str, object]:
    """Derive structural HTML from known fragment and experimental text shapes."""

    blocks: list[str] = []
    for fragment in cast(list[dict[str, object]], dto["fragments"]):
        fragment_type = fragment["fragment_type"]
        attrs = _data_attributes(fragment)
        classes = _class_attribute(_style_tags(fragment))
        if fragment_type == "content":
            tag = "aside" if "block:admonition" in _style_tags(fragment) else "p"
            blocks.append(f"<{tag}{attrs}{classes}>{_html_runs(fragment)}</{tag}>")
        elif fragment_type == "attributed":
            how = f" ({fragment['how']})" if fragment.get("how") else ""
            prefix = html.escape(f"{str(fragment['who']).upper()}{how}: ")
            blocks.append(f"<p{attrs}{classes}>{prefix}{_html_runs(fragment)}</p>")
        elif fragment_type == "kv":
            rows = "\n".join(
                f"<div><dt>{html.escape(str(row['key']))}</dt>"
                f"<dd>: {html.escape(str(row['value']))}</dd></div>"
                for row in cast(list[dict[str, object]], fragment.get("content", []))
            )
            blocks.append(f"<dl{attrs}{classes}>{rows}</dl>")
        elif fragment_type == "choice":
            marker = "1" if fragment.get("available", True) else "x"
            reason = (
                f" [locked: {fragment['unavailable_reason']}]"
                if fragment.get("unavailable_reason")
                else ""
            )
            text = html.escape(f"{marker}) {fragment['text']}{reason}")
            blocks.append(f"<p{attrs}{classes}>{text}</p>")
        elif fragment_type == "media":
            role = fragment.get("media_role") or "media"
            fallback = fragment.get("fallback_text") or fragment.get("content")
            text = html.escape(f"[{role}: {fallback}]")
            blocks.append(f"<figure{attrs}{classes}><figcaption>{text}</figcaption></figure>")
        elif fragment_type == "group":
            members = " ".join(str(value) for value in fragment.get("member_ids", []))
            blocks.append(
                f'<div{attrs}{classes} data-member-ids="{html.escape(members, quote=True)}"'
                ' aria-hidden="true"></div>'
            )

    for event in cast(list[dict[str, object]], dto.get("ux_events", [])):
        text = html.escape(f"[{event['severity']}] {event['message']}")
        event_id = html.escape(str(event["event_id"]), quote=True)
        role = "alert" if event["presentation"] == "interrupt" else "status"
        blocks.append(
            f'<aside data-event-id="{event_id}" role="{role}">{text}</aside>'
        )

    markup = "\n".join(blocks)
    parser = _ReadableHtml()
    parser.feed(markup)
    plain_text = "\n".join(
        line
        for line in "".join(parser.parts).splitlines()
        if line
    )
    return {
        "markup": markup,
        "plain_text": plain_text,
        "manifest": structural_manifest(dto),
    }


def _rich_style(tokens: list[str], styles: Mapping[str, str]) -> str | None:
    matched = [styles[token] for token in tokens if token in styles]
    return " ".join(matched) or None


def realize_terminal(
    dto: Mapping[str, object],
    *,
    styles: Mapping[str, str] = DEFAULT_TERMINAL_STYLES,
) -> tuple[object, dict[str, object]]:
    """Build a Rich Text value and a serializable, ANSI-free inspection record."""

    from rich.console import Console
    from rich.text import Text

    output = Text()

    def add_line(line: Text) -> None:
        if output.plain:
            output.append("\n")
        output.append_text(line)

    for fragment in cast(list[dict[str, object]], dto["fragments"]):
        fragment_type = fragment["fragment_type"]
        if fragment_type in {"content", "attributed"}:
            line = Text()
            if fragment_type == "attributed":
                how = f" ({fragment['how']})" if fragment.get("how") else ""
                line.append(f"{str(fragment['who']).upper()}{how}: ", style="bold")
            fragment_tokens = _style_tags(fragment)
            for run in _text_runs(fragment):
                run_tokens = [str(value) for value in run.get("classes", [])]
                run_style = _rich_style(fragment_tokens + run_tokens, styles)
                line.append(str(run["text"]), style=run_style)
            add_line(line)
        elif fragment_type == "kv":
            for row in cast(list[dict[str, object]], fragment.get("content", [])):
                add_line(Text(f"{row['key']}: {row['value']}"))
        elif fragment_type == "choice":
            marker = "1" if fragment.get("available", True) else "x"
            reason = (
                f" [locked: {fragment['unavailable_reason']}]"
                if fragment.get("unavailable_reason")
                else ""
            )
            style = _rich_style(_style_tags(fragment), styles)
            add_line(Text(f"{marker}) {fragment['text']}{reason}", style=style))
        elif fragment_type == "media":
            role = fragment.get("media_role") or "media"
            fallback = fragment.get("fallback_text") or fragment.get("content")
            add_line(Text(f"[{role}: {fallback}]"))

    for event in cast(list[dict[str, object]], dto.get("ux_events", [])):
        style = _rich_style([f"ux:{event['severity']}"], styles)
        add_line(Text(f"[{event['severity']}] {event['message']}", style=style))

    stream = io.StringIO()
    Console(file=stream, color_system=None, no_color=True, width=200).print(
        output,
        soft_wrap=True,
        end="",
    )
    inspection = {
        "rich_plain": output.plain,
        "rich_spans": [
            {"start": span.start, "end": span.end, "style": str(span.style)}
            for span in output.spans
        ],
        "no_color": stream.getvalue(),
        "manifest": structural_manifest(dto),
    }
    return output, inspection


def structural_manifest(dto: Mapping[str, object]) -> dict[str, object]:
    """Expose the identity, structure, fallback, and event fields audited here."""

    fragments = cast(list[dict[str, object]], dto["fragments"])
    return {
        "fragment_order": [fragment["uid"] for fragment in fragments],
        "provenance": {
            str(fragment["uid"]): {
                key: fragment[key]
                for key in ("origin_id", "source_id")
                if key in fragment
            }
            for fragment in fragments
        },
        "groups": {
            str(fragment["uid"]): fragment.get("member_ids", [])
            for fragment in fragments
            if fragment["fragment_type"] == "group"
        },
        "choices": [
            {
                "uid": fragment["uid"],
                "edge_id": fragment["edge_id"],
                "available": fragment.get("available", True),
                "unavailable_reason": fragment.get("unavailable_reason"),
            }
            for fragment in fragments
            if fragment["fragment_type"] == "choice"
        ],
        "media_fallbacks": {
            str(fragment["uid"]): fragment.get("fallback_text")
            for fragment in fragments
            if fragment["fragment_type"] == "media"
        },
        "ux_event_order": [
            event["event_id"]
            for event in cast(list[dict[str, object]], dto.get("ux_events", []))
        ],
        "ux_events": [
            {
                key: event[key]
                for key in (
                    "event_id",
                    "event_type",
                    "message",
                    "presentation",
                    "replay",
                    "severity",
                    "details",
                )
            }
            for event in cast(list[dict[str, object]], dto.get("ux_events", []))
        ],
    }


def _advisory_tokens(dto: Mapping[str, object]) -> list[str]:
    tokens: set[str] = set()
    for fragment in cast(list[dict[str, object]], dto["fragments"]):
        tokens.update(_style_tags(fragment))
        for run in _text_runs(fragment):
            tokens.update(str(value) for value in run.get("classes", []))
    return sorted(tokens)


def build_report() -> dict[str, object]:
    """Build every inspectable stage for both diagnostic bundles."""

    reports = []
    for path in SOURCE_PATHS:
        source = json.loads(path.read_text(encoding="utf-8"))
        normalized, authoring_adapter = adapt_authored_bundle(source)
        _, terminal = realize_terminal(normalized)
        reports.append(
            {
                "bundle_id": source["bundle_id"],
                "authored": source,
                "authoring_adapter": authoring_adapter,
                "normalized": normalized,
                "html": realize_html(normalized),
                "terminal": terminal,
                "plain_fallback": readable_text(normalized),
                "safe_classes": {
                    token: safe_class_token(token)
                    for token in _advisory_tokens(normalized)
                },
            }
        )
    return {
        "status": "experimental",
        "projection_realization_matrix": PROJECTION_REALIZATION_MATRIX,
        "bundles": reports,
    }


def write_report(path: Path = REPORT_PATH) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(build_report(), indent=2) + "\n", encoding="utf-8")
    return path


if __name__ == "__main__":
    print(write_report())
