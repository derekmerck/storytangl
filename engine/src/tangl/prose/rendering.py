"""Bounded recursive text rendering for narrative adapters.

The renderer consumes the namespace already assembled for a phase context. It
does not own graph state, journal emission, or a general content-product model.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable

import jinja2

from tangl.utils.rejinja import RecursiveTemplate
from tangl.vm.ctx import VmPhaseCtx


class RecursiveRenderError(RuntimeError):
    """Raised when generated template text cannot reach a stable result."""


@dataclass(slots=True)
class TextRenderSession:
    """Render related text segments with shared, ephemeral discourse state."""

    ctx: VmPhaseCtx
    discourse: dict[str, Any] = field(default_factory=dict)
    max_depth: int = 32
    environment: jinja2.Environment = field(default_factory=jinja2.Environment)

    def render(
        self,
        content: str,
        *,
        source: object | None = None,
        subject: object | None = None,
        bindings: dict[str, Any] | None = None,
    ) -> str:
        """Render text against the source's gathered namespace.

        ``subject`` is the template-visible child binding for nested rendering.
        Jinja reserves ``self`` for its own template reference, so it cannot be
        repurposed as an authored variable.
        """
        scope_source = source if source is not None else self.ctx.cursor
        scope = dict(self.ctx.get_ns(scope_source))
        if bindings:
            scope.update(bindings)
        scope["discourse"] = self.discourse
        scope["render_child"] = self.render_child
        if subject is not None:
            scope["subject"] = subject

        return self._render_recursive(content, scope)

    def render_child(
        self,
        content: str,
        subject: object,
        *,
        source: object | None = None,
        bindings: dict[str, Any] | None = None,
    ) -> str:
        """Render child text with a fresh gathered scope and child subject."""
        return self.render(
            content,
            source=source,
            subject=subject,
            bindings=bindings,
        )

    def render_segments(
        self,
        segments: Iterable[str],
        *,
        source: object | None = None,
    ) -> list[str]:
        """Render consecutive segments while preserving this session's discourse."""
        return [self.render(segment, source=source) for segment in segments]

    def _render_recursive(self, content: str, scope: dict[str, Any]) -> str:
        current = content
        seen_templates: set[str] = set()
        seen_outputs: set[str] = set()

        for _ in range(self.max_depth):
            if current in seen_templates:
                raise RecursiveRenderError("Recursive template cycle detected")
            seen_templates.add(current)

            template = self.environment.from_string(
                current,
                template_class=RecursiveTemplate,
            )
            rendered = template.render_once(scope).strip()
            if not _contains_template_syntax(rendered):
                return rendered
            if rendered in seen_outputs:
                raise RecursiveRenderError("Recursive template produced repeated output")
            seen_outputs.add(rendered)
            current = rendered

        raise RecursiveRenderError(
            f"Recursive template exceeded maximum depth ({self.max_depth})",
        )


def render_text(
    content: str,
    *,
    ctx: VmPhaseCtx,
    source: object | None = None,
    subject: object | None = None,
    discourse: dict[str, Any] | None = None,
) -> str:
    """Render one text value through the default bounded recursive session."""
    return TextRenderSession(
        ctx=ctx,
        discourse=discourse if discourse is not None else {},
    ).render(
        content,
        source=source,
        subject=subject,
    )


def _contains_template_syntax(content: str) -> bool:
    return "{{" in content or "{%" in content


__all__ = ["RecursiveRenderError", "TextRenderSession", "render_text"]
