"""
Dialog parsing and rendering helpers.

Dialog blocks use Obsidian's callout header syntax::

    > [!POV|speaker.attentive]+ Speaker Name
    > I am speaking now.

The bar separates explicit mode from the binding/presentation chain. Without
it, the frontend supplies the default mode, normally dialog. Parsing never
consults a namespace. Realization consumes the leading chain candidate only
when it binds a speaker. The optional title is adopted through the current
scope or remains literal; a leading backslash forces a literal title. The
optional ``+`` or ``-`` fold marker is accepted without adding a widget.

Only paragraphs whose first line claims ``> [!`` syntax are dialog callouts.
Other prose, including ordinary block quotes, is emitted as narration.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from collections.abc import Iterator
from typing import Any, Mapping
from uuid import UUID

from tangl.journal.fragments import AttributedFragment, ContentFragment
from tangl.presentation.hints import PresentationHints
from tangl.utils.sanitize_str import sanitize_str
from tangl.vm.ctx import VmPhaseCtx

from .mu_block import DialogSpeakerBinding, MuBlock, MuBlockHandler, NameResolver, SpeakerResolver
from .literals import code_regions


@dataclass(frozen=True, slots=True)
class _DialogHeader:
    dialog_class: str
    label: str | None
    dialog_mode: str
    literal_label: bool = False


def _normalized_text(value: Any) -> str:
    return str(value or "").strip()


def _tag_value(value: Any) -> str | None:
    text = _normalized_text(value)
    if not text:
        return None
    return sanitize_str(text).casefold()


def _model_payload(value: Any) -> Any:
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        return model_dump(mode="python")
    if isinstance(value, dict):
        return dict(value)
    return value


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


class DialogMuBlock(MuBlock):
    """Separate authored mode, binding/presentation chain, and title source."""

    dialog_class: str = ""
    dialog_mode: str = "dialog"
    literal_label: bool = False

    @property
    def binding_candidate(self) -> str | None:
        return self.dialog_class.split(".", 1)[0] or None

    @property
    def presentation_chain(self) -> list[str]:
        return self.dialog_class.split(".")[1:]

    def prepare_fragment(
        self, *, source_id: UUID | None = None, ns: Mapping[str, object] | None = None,
        ctx: VmPhaseCtx | None = None, name_resolver: NameResolver | None = None,
        speaker_resolver: SpeakerResolver | None = None,
    ) -> ContentFragment:
        """Resolve provider metadata into a fresh fragment before body realization."""
        speaker_key = speaker_id = speaker_label = speaker_name = None
        media_payload = None
        if speaker_resolver is not None:
            binding = speaker_resolver(self.binding_candidate, self.label, self.literal_label)
        else:
            candidate = ns.get(self.binding_candidate) if ns and self.binding_candidate else None
            binding = (
                DialogSpeakerBinding(key=self.binding_candidate, subject=candidate)
                if candidate is not None and not isinstance(
                    candidate, (str, bytes, int, float, bool, dict, list, tuple, set),
                )
                else None
            )
            if binding is None and not self.literal_label:
                binding = _speaker_binding(self.label, ns)
        presentation = (
            self.presentation_chain
            if binding is not None and binding.key == self.binding_candidate
            else [term for term in self.dialog_class.split(".") if term]
        )
        attitude = ".".join(presentation) or None
        dialog_class = ".".join([self.dialog_mode, *presentation])
        style_tags = ["dialog"]
        if dialog_class_tag := _tag_value(dialog_class):
            style_tags.append(f"dialog_class:{dialog_class_tag}")
        if dialog_mode_tag := _tag_value(self.dialog_mode):
            style_tags.append(f"dialog_mode:{dialog_mode_tag}")
        if attitude_tag := _tag_value(attitude):
            style_tags.append(f"attitude:{attitude_tag}")
        if binding is None and self.label is None:
            if self.dialog_mode.casefold() == "dialog":
                raise ValueError(
                    f"source {self.source_id or source_id}: dialog requires a scoped binding: "
                    f"{self.dialog_class!r}"
                )
            return ContentFragment(
                content="", source_id=self.source_id or source_id,
                tags=set(style_tags[1:]),
                hints=PresentationHints(
                    style_name=self.style_cls or self.dialog_mode,
                    style_tags=style_tags,
                    style_dict=dict(self.style_dict),
                ),
            )
        style_dict: dict[str, str] = {}
        if binding is not None:
            subject = binding.subject
            speaker_key = binding.key
            params = (
                dict(binding.title_reference.params)
                if binding.title_reference is not None else {"form": "label"}
            )
            resolved_name = (
                name_resolver(subject, **params)
                if name_resolver is not None and (self.label is None or binding.title_reference)
                else None
            )
            speaker_name = (
                resolved_name if resolved_name is not None
                else _speaker_display_name(subject, self.label)
            )
            media_payload = _speaker_media_payload(
                subject,
                dialog_class=dialog_class,
                attitude=attitude,
                ctx=ctx,
            )

            uid = getattr(subject, "uid", None)
            if uid is not None:
                speaker_id = str(uid)

            get_label = getattr(subject, "get_label", None)
            if callable(get_label):
                label = get_label()
                if isinstance(label, str) and label.strip():
                    speaker_label = label.strip()

            style_dict = _speaker_style_dict(subject, dialog_class=dialog_class)

        if self.label is not None and (
            binding is None or binding.title_reference is None
        ):
            speaker_name = self.label

        if not speaker_name:
            speaker_name = _normalized_text(self.label) or "narrator"

        if speaker_tag := _tag_value(speaker_label or self.label):
            style_tags.append(f"speaker:{speaker_tag}")
        if speaker_key_tag := _tag_value(speaker_key):
            style_tags.append(f"speaker_key:{speaker_key_tag}")

        hints = PresentationHints(
            style_name=self.style_cls or self.dialog_mode.lower(),
            style_tags=style_tags,
            style_dict=style_dict | self.style_dict,
        )
        return AttributedFragment(
            content="",
            who=speaker_name,
            how=dialog_class,
            media="dialog_im" if media_payload else "",
            source_id=self.source_id or source_id,
            tags=set(style_tags[1:]),
            hints=hints,
            speaker_key=speaker_key,
            speaker_id=speaker_id,
            speaker_label=speaker_label,
            speaker_name=speaker_name,
            speaker_attitude=attitude,
            dialog_mode=self.dialog_mode,
            media_payload=media_payload,
        )


class DialogHandler(MuBlockHandler):
    """Parse and render dialog micro-blocks."""

    DIALOG_CLAIM_PATTERN = re.compile(r"^>\s*\[!")
    DEFAULT_MODE = "dialog"
    DIALOG_HEADER_PATTERN = re.compile(
        r"^>\s*\[!(?P<dialog_class>[^\]\s]+)\](?P<fold>[+-])?"
        r"(?:[ \t]+(?P<label>\S(?:.*\S)?))?[ \t]*$"
    )

    @staticmethod
    def paragraph_spans(text: str) -> Iterator[tuple[int, int]]:
        """Locate the existing paragraphs without splitting literal code regions."""
        protected = list(code_regions(text))
        start = 0
        for separator in re.finditer(r"\n(?:[ \t]*\n)+", text):
            if any(a <= separator.start() and separator.end() <= b for a, b in protected):
                continue
            if text[start:separator.start()].strip():
                yield start, separator.start()
            start = separator.end()
        if text[start:].strip():
            yield start, len(text)

    @classmethod
    def _paragraphs(cls, text: str) -> list[str]:
        return [text[start:end].strip() for start, end in cls.paragraph_spans(text)]

    @staticmethod
    def _paragraph_lines(paragraph: str) -> list[str]:
        return [line for line in paragraph.split("\n") if line.strip()]

    @classmethod
    def _parse_dialog_header(cls, header: str) -> _DialogHeader | None:
        if not cls.DIALOG_CLAIM_PATTERN.match(header):
            return None
        match = cls.DIALOG_HEADER_PATTERN.fullmatch(header)
        if match is None:
            raise ValueError(f"Invalid dialog syntax: {header}")
        raw_class = match.group("dialog_class")
        if raw_class.count("|") > 1:
            raise ValueError(f"Invalid dialog syntax: {header}")
        mode, separator, chain = raw_class.partition("|")
        if separator and not mode:
            raise ValueError(f"Invalid dialog syntax: {header}")
        title = match.group("label")
        literal = False
        if title is not None:
            slashes = len(title) - len(title.lstrip("\\"))
            literal = bool(slashes % 2)
            title = "\\" * (slashes // 2) + title[slashes:]
        return _DialogHeader(
            dialog_class=chain if separator else raw_class,
            dialog_mode=mode if separator else cls.DEFAULT_MODE,
            label=title, literal_label=literal,
        )

    @classmethod
    def has_mu_blocks(cls, text: str) -> bool:
        for paragraph in cls._paragraphs(text):
            lines = cls._paragraph_lines(paragraph)
            if not lines:
                continue
            try:
                if cls._parse_dialog_header(lines[0]) is not None:
                    return True
            except ValueError:
                return True
        return False

    @classmethod
    def find_malformed_header(cls, text: str) -> str | None:
        """Return the first malformed line that claims dialog callout syntax."""
        for paragraph in cls._paragraphs(text):
            lines = cls._paragraph_lines(paragraph)
            if not lines:
                continue
            try:
                cls._parse_dialog_header(lines[0])
            except ValueError:
                return lines[0]
        return None

    @classmethod
    def parse(
        cls, text: str, *, source_id: UUID | None = None,
    ) -> list[DialogMuBlock]:
        mu_blocks: list[DialogMuBlock] = []

        for paragraph in cls._paragraphs(text):
            lines = cls._paragraph_lines(paragraph)
            header = cls._parse_dialog_header(lines[0]) if lines else None
            if header is not None:
                mu_blocks.append(
                    cls._parse_dialog_paragraph(paragraph, source_id=source_id)
                )
            else:
                mu_blocks.append(
                    DialogMuBlock(
                        text=paragraph.strip(),
                        label=None,
                        dialog_mode="narration",
                        source_id=source_id,
                    )
                )

        return mu_blocks

    @classmethod
    def _parse_dialog_paragraph(
        cls, paragraph: str, *, source_id: UUID | None
    ) -> DialogMuBlock:
        lines = cls._paragraph_lines(paragraph)
        header = lines[0] if lines else ""
        parsed_header = cls._parse_dialog_header(header)
        if parsed_header is None:
            raise ValueError(f"Invalid dialog syntax: {header}")
        body_lines = (cls._strip_dialog_prefix(line) for line in lines[1:])
        body_text = " ".join(filter(None, body_lines))

        return DialogMuBlock(
            text=body_text,
            label=parsed_header.label,
            dialog_class=parsed_header.dialog_class,
            dialog_mode=parsed_header.dialog_mode,
            literal_label=parsed_header.literal_label,
            source_id=source_id,
        )

    @staticmethod
    def _strip_dialog_prefix(line: str) -> str:
        return re.sub(r"^>\s*", "", line).strip()
