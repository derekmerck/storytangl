"""Shared authored micro-block values and ordered fragment projection.

Values parsed for one turn and values embedded in a graph use the same schema.
Binding/rendered data lives only in the projected journal fragments.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable, Mapping, Sequence
from enum import Enum
from typing import Self
from uuid import UUID

from pydantic import Field, model_validator

from tangl.core.bases import Unstructurable
from tangl.journal.fragments import ContentFragment
from tangl.presentation.hints import PresentationHints
from tangl.utils.enum_plus import EnumPlusMixin
from tangl.vm.ctx import VmPhaseCtx

from .rendering import TextRenderSession


class ReferenceIntent(EnumPlusMixin, str, Enum):
    AUTO = "auto"
    ANONYMOUS = "anonymous"
    PROPER = "proper"


type RealizationValue = str | int | float | bool | None
type RealizationParams = dict[str, RealizationValue]


class ConceptReference(Unstructurable):
    """A namespace referent and wording intent, independent of template syntax."""

    ref: str
    intent: ReferenceIntent = ReferenceIntent.AUTO
    introduce: bool = False
    params: RealizationParams = Field(
        default_factory=dict, json_schema_extra={"include": True},
    )


PartResolver = Callable[[list[str | ConceptReference]], str]
NameResolver = Callable[[object], str | None]
SpeakerResolver = Callable[[str], object]


class MuBlock(Unstructurable):
    """Authored narrative unit; optional ownership determines whether it persists."""

    text: str | list[str | ConceptReference] | None = Field(
        default=None, json_schema_extra={"include": True, "unstructurable": True},
    )
    template: str | None = None
    label: str | None = None
    style_cls: str | None = None
    style_dict: dict[str, str] = Field(default_factory=dict, json_schema_extra={"include": True})
    source_id: UUID | None = None

    @model_validator(mode="after")
    def _exclusive_body(self) -> Self:
        if self.text is not None and self.template is not None:
            raise ValueError("A micro-block accepts text or template, not both")
        return self

    def prepare_fragment(
        self, *, source_id: UUID | None = None, ns: Mapping[str, object] | None = None,
        ctx: VmPhaseCtx | None = None, name_resolver: NameResolver | None = None,
        speaker_resolver: SpeakerResolver | None = None,
    ) -> ContentFragment:
        """Prepare fresh metadata before the handler realizes the body."""
        hints = None
        if self.style_cls or self.style_dict:
            hints = PresentationHints(style_name=self.style_cls, style_dict=dict(self.style_dict))
        return ContentFragment(content="", source_id=self.source_id or source_id, hints=hints)


class MuBlockHandler(ABC):
    """Parse authored structure, then project it through one ordered rendering path."""

    @classmethod
    @abstractmethod
    def has_mu_blocks(cls, text: str) -> bool:
        raise NotImplementedError

    @classmethod
    @abstractmethod
    def parse(cls, text: str, *, source_id: UUID | None = None) -> list[MuBlock]:
        raise NotImplementedError

    @classmethod
    def render(
        cls, mu_blocks: Sequence[MuBlock], *, ns: Mapping[str, object] | None = None,
        ctx: VmPhaseCtx | None = None, source_id: UUID | None = None,
        name_resolver: NameResolver | None = None, parts_resolver: PartResolver | None = None,
        speaker_resolver: SpeakerResolver | None = None,
    ) -> list[ContentFragment]:
        fragments: list[ContentFragment] = []
        for authored in mu_blocks:
            # Bind the label before realizing its body, without touching the source.
            fragment = authored.prepare_fragment(
                ns=ns, ctx=ctx, source_id=source_id, name_resolver=name_resolver,
                speaker_resolver=speaker_resolver,
            )
            if authored.template is not None:
                if ctx is None:
                    raise ValueError("An explicit micro-block template requires a phase context")
                session = TextRenderSession(ctx=ctx)
                content = session.environment.from_string(authored.template).render(ns or {})
            elif isinstance(authored.text, str):
                content = authored.text
            elif parts_resolver is not None:
                content = parts_resolver(authored.text or [])
            else:
                content = "".join(authored.text or [])
            fragments.append(fragment.model_copy(update={"content": content}))
        return fragments
