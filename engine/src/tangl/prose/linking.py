"""Pure exact-source lowering into the existing authored reference vocabulary."""
from __future__ import annotations

from collections.abc import Sequence
import re

from .dialog import DialogHandler, DialogMuBlock
from .literals import code_regions
from .mu_block import ConceptReference, MuBlock


type AdoptionTable = dict[str, list[ConceptReference]]

_INTRO = re.compile(r"#intro(?!\w)")
_ATTACHED_INTRO = re.compile(r"[ \t]*#intro(?!\w)")


def _has_template_syntax(text: str) -> bool:
    return any(delimiter in text for delimiter in ("{{", "{%", "{#"))


def link_text(
    text: str, adoptions: AdoptionTable, *, source: str,
    unit_index: int = 0, offset: int = 0,
) -> list[str | ConceptReference]:
    """Lower exact narration, retaining source offsets and detached form intent.

    Odd backslash runs escape a name/marker; pairs emit one literal slash.
    Unrelated slashes, code and units containing Jinja delimiters stay literal.
    """
    if _has_template_syntax(text):
        return [text]
    spellings = sorted((spelling for spelling in adoptions if spelling),
                       key=lambda spelling: (-len(spelling), spelling))
    pattern = None
    if spellings:
        pattern = re.compile(r"(?<!\w)(?:" + "|".join(map(re.escape, spellings)) + r")(?!\w)")
    protected = iter(code_regions(text))
    region = next(protected, None)
    parts: list[str | ConceptReference] = []
    literal: list[str] = []
    position = 0
    while position < len(text):
        if region is not None and position == region[0]:
            literal.append(text[region[0]:region[1]])
            position = region[1]
            region = next(protected, None)
            continue
        if text[position] == "\\":
            end = position + 1
            while end < len(text) and text[end] == "\\":
                end += 1
            name = (
                pattern.match(text, end, region[0] if region else len(text))
                if pattern is not None else None
            )
            marker = _INTRO.match(text, end)
            if name is not None or marker is not None:
                count = end - position
                literal.append("\\" * (count // 2))
                position = end
                if count % 2:
                    token_end = name.end() if name is not None else marker.end()
                    attached = _ATTACHED_INTRO.match(text, token_end) if name is not None else None
                    if attached is not None:
                        token_end = attached.end()
                    literal.append(text[end:token_end])
                    position = token_end
                continue
            literal.append(text[position:end])
            position = end
            continue
        name = (
            pattern.match(text, position, region[0] if region else len(text))
            if pattern is not None else None
        )
        if name is not None:
            candidates = adoptions[name.group()]
            if len(candidates) != 1:
                symbols = ", ".join(sorted(candidate.ref for candidate in candidates))
                raise ValueError(
                    f"{source}: unit {unit_index}, offset {offset + position}: "
                    f"ambiguous {name.group()!r}; candidates: {symbols}"
                )
            attached = _ATTACHED_INTRO.match(text, name.end())
            if literal:
                parts.append("".join(literal))
                literal.clear()
            reference = candidates[0]
            parts.append(reference.model_copy(update={
                "introduce": attached is not None, "params": dict(reference.params),
            }))
            position = attached.end() if attached is not None else name.end()
            continue
        if _INTRO.match(text, position):
            raise ValueError(
                f"{source}: unit {unit_index}, offset {offset + position}: unmatched #intro"
            )
        literal.append(text[position])
        position += 1
    if literal or not parts:
        parts.append("".join(literal))
    return parts


def prepare_prose(
    units: Sequence[MuBlock], adoptions: AdoptionTable, *, source: str,
) -> list[MuBlock]:
    """Prepare ephemeral units; source and custom preparation methods stay owned."""
    prepared: list[MuBlock] = []
    for index, authored in enumerate(units):
        text = authored.text
        if not isinstance(text, str) or authored.template is not None or _has_template_syntax(text):
            prepared.append(authored)
            continue
        origin = f"{source}; source {authored.source_id or source}"
        if isinstance(authored, DialogMuBlock):
            if authored.dialog_mode.casefold() != "narration":
                prepared.append(authored)
                continue
        elif DialogHandler.has_mu_blocks(text):
            if type(authored) is not MuBlock:
                # Custom raw syntax belongs to that type; structured custom units
                # retain their normal preparation behavior without flattening.
                prepared.append(authored)
                continue
            for start, end in DialogHandler.paragraph_spans(text):
                paragraph = text[start:end]
                parsed = DialogHandler.parse(
                    paragraph, source_id=authored.source_id,
                )[0]
                if DialogHandler.DIALOG_CLAIM_PATTERN.match(paragraph.lstrip()):
                    prepared.append(parsed.model_copy(update={
                        "style_cls": authored.style_cls, "style_dict": dict(authored.style_dict),
                    }))
                else:
                    parts = link_text(paragraph, adoptions, source=origin,
                                      unit_index=index, offset=start)
                    prepared.append(authored.model_copy(update={"text": parts}))
            continue
        parts = link_text(text, adoptions, source=origin, unit_index=index)
        prepared.append(authored.model_copy(update={"text": parts}))
    return prepared
