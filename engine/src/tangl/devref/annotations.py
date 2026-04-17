from __future__ import annotations

from .models import TopicAnnotation


def _split_csv(value: str) -> list[str]:
    return [part.strip() for part in value.split(",") if part.strip()]


def _parse_body(body: str) -> TopicAnnotation | None:
    options: dict[str, str] = {}
    for raw_line in body.splitlines():
        stripped = raw_line.strip()
        if not stripped.startswith(":") or ":" not in stripped[1:]:
            continue
        key, _, value = stripped[1:].partition(":")
        options[key.strip()] = value.strip()

    if "topics" not in options or "relation" not in options:
        return None

    return TopicAnnotation(
        topics=_split_csv(options["topics"]),
        facets=_split_csv(options.get("facets", "")),
        relation=options["relation"].strip(),
        related=_split_csv(options.get("related", "")),
    )


def extract_storytangl_topic_annotations(text: str) -> list[TopicAnnotation]:
    """Parse all ``storytangl-topic`` annotations from raw text."""

    annotations: list[TopicAnnotation] = []
    lines = text.splitlines()
    index = 0
    while index < len(lines):
        stripped = lines[index].strip()
        if stripped == ".. storytangl-topic::":
            body: list[str] = []
            index += 1
            while index < len(lines):
                candidate = lines[index]
                if candidate.strip() and not candidate.startswith((" ", "\t")):
                    break
                if candidate.strip():
                    body.append(candidate)
                index += 1
            annotation = _parse_body("\n".join(body))
            if annotation is not None:
                annotations.append(annotation)
            continue
        if stripped == "```{storytangl-topic}":
            body = []
            index += 1
            while index < len(lines) and lines[index].strip() != "```":
                body.append(lines[index])
                index += 1
            annotation = _parse_body("\n".join(body))
            if annotation is not None:
                annotations.append(annotation)
        index += 1
    return annotations
