"""
Dialog parsing and rendering helpers.

Dialog blocks follow a lightweight Obsidian-style admonition syntax::

    > [!POV] Speaker Name
    > I am speaking now.

Leading ``>`` markers denote dialog paragraphs; non-dialog paragraphs are
emitted as narration micro-blocks.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Mapping
from uuid import UUID

from tangl.journal.discourse import AttributedFragment
from tangl.journal.content import ContentFragment, PresentationHints

from .mu_block import MuBlock, MuBlockHandler


@dataclass(slots=True)
class DialogSpeakerBinding:
    """Resolved speaker binding for a dialog micro-block."""

    key: str | None
    subject: Any


def _normalized_text(value: Any) -> str:
    return str(value or "").strip()


def _model_payload(value: Any) -> Any:
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        return model_dump(mode="python")
    if isinstance(value, dict):
        return dict(value)
    return value


def _split_dialog_class(dialog_class: str) -> tuple[str, str | None]:
    raw = _normalized_text(dialog_class) or "narration"
    if "." not in raw:
        return raw, None
    mode, attitude = raw.split(".", 1)
    return mode or "narration", attitude or None


def _speaker_display_name(subject: Any, fallback: str | None) -> str:
    name = getattr(subject, "name", None)
    if isinstance(name, str) and name.strip():
        return name.strip()

    get_label = getattr(subject, "get_label", None)
    if callable(get_label):
        label = get_label()
        if isinstance(label, str) and label.strip():
            return label.strip()

    return _normalized_text(fallback) or "narrator"


def _speaker_style_dict(subject: Any, *, dialog_class: str) -> dict[str, str]:
    get_dialog_style = getattr(subject, "get_dialog_style", None)
    if not callable(get_dialog_style):
        return {}

    style_dict = get_dialog_style(dialog_class=dialog_class)
    if isinstance(style_dict, dict):
        return {str(key): str(value) for key, value in style_dict.items()}
    return {}


def _speaker_media_payload(subject: Any, *, dialog_class: str, attitude: str | None, ctx: Any) -> Any:
    adapt_look_media_spec = getattr(subject, "adapt_look_media_spec", None)
    if callable(adapt_look_media_spec):
        payload = adapt_look_media_spec(
            ctx=ctx,
            media_role="dialog_im",
            attitude=attitude,
        )
        payload = _model_payload(payload)
        if isinstance(payload, dict) and any(bool(item) for item in payload.values()):
            return payload

    get_dialog_image = getattr(subject, "get_dialog_image", None)
    if callable(get_dialog_image):
        image = get_dialog_image(dialog_class=dialog_class)
        if image is None:
            return None

        get_label = getattr(image, "get_label", None)
        if callable(get_label):
            return {"ref": get_label(), "media_role": "dialog_im"}
        return {"ref": str(image), "media_role": "dialog_im"}

    return None


def _speaker_binding(label: str | None, ns: Mapping[str, Any] | None) -> DialogSpeakerBinding | None:
    normalized_label = _normalized_text(label)
    if not normalized_label or not isinstance(ns, Mapping):
        return None

    direct = ns.get(normalized_label)
    if direct is not None:
        return DialogSpeakerBinding(key=normalized_label, subject=direct)

    lower_label = normalized_label.casefold()
    for key, value in ns.items():
        if value is None or isinstance(value, (str, bytes, int, float, bool, dict, list, tuple, set)):
            continue

        if isinstance(key, str) and key.casefold() == lower_label:
            return DialogSpeakerBinding(key=key, subject=value)

        name = getattr(value, "name", None)
        if isinstance(name, str) and name.strip().casefold() == lower_label:
            return DialogSpeakerBinding(key=str(key) if isinstance(key, str) else None, subject=value)

        get_label = getattr(value, "get_label", None)
        if callable(get_label):
            subject_label = get_label()
            if isinstance(subject_label, str) and subject_label.strip().casefold() == lower_label:
                return DialogSpeakerBinding(key=str(key) if isinstance(key, str) else None, subject=value)

        goes_by = getattr(value, "goes_by", None)
        if callable(goes_by):
            try:
                if goes_by(normalized_label):
                    return DialogSpeakerBinding(key=str(key) if isinstance(key, str) else None, subject=value)
            except Exception:
                continue

    return None


@dataclass(slots=True)
class DialogMuBlock(MuBlock):
    """Dialog utterance with optional speaker metadata."""

    dialog_class: str = "narration"
    dialog_mode: str | None = None
    attitude: str | None = None
    speaker_key: str | None = None
    speaker_id: str | None = None
    speaker_label: str | None = None
    speaker_name: str | None = None
    presentation_hints: PresentationHints | None = None
    media_payload: Any = None

    def bind(self, *, ns: Mapping[str, Any] | None = None, ctx: Any = None) -> "DialogMuBlock":
        """Resolve speaker metadata against the current render namespace."""
        dialog_mode, attitude = _split_dialog_class(self.dialog_class)
        self.dialog_mode = dialog_mode
        self.attitude = attitude

        binding = _speaker_binding(self.label, ns)
        style_dict: dict[str, str] = {}
        if binding is not None:
            subject = binding.subject
            self.speaker_key = binding.key
            self.speaker_name = _speaker_display_name(subject, self.label)
            self.media_payload = _speaker_media_payload(
                subject,
                dialog_class=self.dialog_class,
                attitude=attitude,
                ctx=ctx,
            )

            uid = getattr(subject, "uid", None)
            if uid is not None:
                self.speaker_id = str(uid)

            get_label = getattr(subject, "get_label", None)
            if callable(get_label):
                label = get_label()
                if isinstance(label, str) and label.strip():
                    self.speaker_label = label.strip()

            style_dict = _speaker_style_dict(subject, dialog_class=self.dialog_class)

        if not self.speaker_name:
            self.speaker_name = _normalized_text(self.label) or "narrator"

        style_tags = [
            "dialog",
            f"dialog_class:{self.dialog_class}",
            f"dialog_mode:{(self.dialog_mode or 'narration').lower()}",
        ]
        if self.speaker_label:
            style_tags.append(f"speaker:{self.speaker_label}")
        elif self.label:
            style_tags.append(f"speaker:{self.label}")
        if self.speaker_key:
            style_tags.append(f"speaker_key:{self.speaker_key}")
        if self.attitude:
            style_tags.append(f"attitude:{self.attitude}")

        self.presentation_hints = PresentationHints(
            style_name=(self.dialog_mode or "narration").lower(),
            style_tags=style_tags,
            style_dict=style_dict,
        )
        return self

    def to_fragment(self) -> AttributedFragment:
        tags: set[str] = {f"dialog_class:{self.dialog_class}"}
        dialog_mode = (self.dialog_mode or "narration").lower()
        tags.add(f"dialog_mode:{dialog_mode}")
        if self.speaker_label:
            tags.add(f"speaker:{self.speaker_label}")
        elif self.label:
            tags.add(f"speaker:{self.label}")
        if self.speaker_key:
            tags.add(f"speaker_key:{self.speaker_key}")
        if self.attitude:
            tags.add(f"attitude:{self.attitude}")

        return AttributedFragment(
            content=self.text,
            who=self.speaker_name or self.label or "narrator",
            how=self.dialog_class,
            media="dialog_im" if self.media_payload else "",
            source_id=self.source_id,
            tags=tags,
            hints=self.presentation_hints,
            speaker_key=self.speaker_key,
            speaker_id=self.speaker_id,
            speaker_label=self.speaker_label,
            speaker_name=self.speaker_name or self.label or "narrator",
            speaker_attitude=self.attitude,
            dialog_mode=self.dialog_mode or "narration",
            media_payload=self.media_payload,
        )


class DialogHandler(MuBlockHandler):
    """Parse and render dialog micro-blocks."""

    DIALOG_PATTERN = re.compile(r"^>\s+\[!", re.MULTILINE)

    @classmethod
    def has_mu_blocks(cls, text: str) -> bool:
        return bool(cls.DIALOG_PATTERN.search(text))

    @classmethod
    def parse(
        cls, text: str, *, source_id: UUID | None = None, **_: object
    ) -> list[DialogMuBlock]:
        paragraphs = re.split(r"\n{2,}", text.strip()) if text.strip() else []
        mu_blocks: list[DialogMuBlock] = []

        for paragraph in paragraphs:
            if paragraph.startswith(">"):
                mu_blocks.append(
                    cls._parse_dialog_paragraph(paragraph, source_id=source_id)
                )
            else:
                mu_blocks.append(
                    DialogMuBlock(
                        text=paragraph.strip(),
                        label=None,
                        dialog_class="narration",
                        source_id=source_id,
                    )
                )

        ns = _.get("ns")
        render_ctx = _.get("ctx")
        return [mu_block.bind(ns=ns, ctx=render_ctx) for mu_block in mu_blocks]

    @classmethod
    def _parse_dialog_paragraph(
        cls, paragraph: str, *, source_id: UUID | None
    ) -> DialogMuBlock:
        lines = [line for line in paragraph.split("\n") if line.strip()]
        header = lines[0]
        header_match = re.match(r">\s*\[!([\w\.-]+)\s*]\s*(\w.*)?", header)
        if header_match is None:
            raise ValueError(f"Invalid dialog syntax: {header}")

        dialog_class = header_match.group(1).strip()
        label = header_match.group(2).strip() if header_match.group(2) else None
        body_lines = (cls._strip_dialog_prefix(line) for line in lines[1:])
        body_text = " ".join(filter(None, body_lines))

        return DialogMuBlock(
            text=body_text,
            label=label,
            dialog_class=dialog_class,
            source_id=source_id,
        )

    @staticmethod
    def _strip_dialog_prefix(line: str) -> str:
        return re.sub(r"^>\s*", "", line).strip()

    @classmethod
    def render(cls, mu_blocks: list[MuBlock]) -> list[ContentFragment]:
        fragments = super().render(mu_blocks)
        return [fragment for fragment in fragments if fragment.content]
