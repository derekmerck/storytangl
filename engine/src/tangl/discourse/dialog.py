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
from uuid import UUID
from tangl.journal.discourse import AttributedFragment
from tangl.journal.content import ContentFragment

from .mu_block import MuBlock, MuBlockHandler


@dataclass(slots=True)
class DialogMuBlock(MuBlock):
    """Dialog utterance with optional speaker metadata."""

    dialog_class: str = "narration"

    def to_fragment(self) -> AttributedFragment:
        tags: set[str] = {f"dialog_class:{self.dialog_class}"}
        if self.label:
            tags.add(f"speaker:{self.label}")

        return AttributedFragment(
            content=self.text,
            who=self.label or "narrator",
            how=self.dialog_class,
            media="",
            source_id=self.source_id,
            tags=tags,
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

        return mu_blocks

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
