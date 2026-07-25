"""Bounded recursive text rendering for narrative adapters.

The renderer consumes the namespace already assembled for a phase context. It
does not own graph state, journal emission, or a general content-product model.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import TypeAlias

import jinja2

from tangl.utils.rejinja import RecursiveTemplate
from tangl.vm.ctx import VmPhaseCtx

Scope: TypeAlias = dict[str, object]


class RecursiveRenderError(RuntimeError):
    """Terminate an unbounded recursive rendering path.

    Why
    ---
    Author-provided recursive text must fail predictably rather than consume
    the Python call stack or emit unresolved template syntax.

    Key Features
    ------------
    Reports template cycles, repeated generated output, and exhausted depth.

    See Also
    --------
    :class:`TextRenderSession`
    """


@dataclass(slots=True)
class _RecursiveRenderState:
    """Active template and output values for one recursive render tree."""

    templates: set[str] = field(default_factory=set)
    outputs: set[str] = field(default_factory=set)


@dataclass(slots=True)
class TextRenderSession:
    """Render related narrative text with shared, ephemeral discourse state.

    Why
    ---
    A renderer needs the phase-assembled namespace and a short-lived place for
    consecutive prose segments to retain focus without mutating graph state.

    Key Features
    ------------
    Renders through :class:`RecursiveTemplate`, provides child ``subject``
    bindings, and bounds recursive output across nested child renders.

    API
    ---
    :meth:`render` produces one text value, :meth:`render_child` binds a child
    subject, and :meth:`render_segments` keeps the same discourse mapping.

    Notes
    -----
    Jinja reserves ``self`` for template references; ``subject`` is the
    author-visible child binding.

    See Also
    --------
    :func:`render_text`, :class:`tangl.vm.runtime.frame.PhaseCtx`
    """

    ctx: VmPhaseCtx
    discourse: Scope = field(default_factory=dict)
    max_depth: int = 32
    environment: jinja2.Environment = field(default_factory=jinja2.Environment)
    _active_state: _RecursiveRenderState | None = field(default=None, init=False, repr=False)

    def render(
        self,
        content: str,
        *,
        source: object | None = None,
        subject: object | None = None,
        bindings: Mapping[str, object] | None = None,
    ) -> str:
        """Render text against the source's gathered namespace.

        ``subject`` is the template-visible child binding for nested rendering.
        Jinja reserves ``self`` for its own template reference, so it cannot be
        repurposed as an authored variable.
        """
        scope_source = source if source is not None else self.ctx.cursor
        scope: Scope = dict(self.ctx.get_ns(scope_source))
        if bindings:
            scope.update(bindings)
        scope["discourse"] = self.discourse
        scope["render_child"] = self.render_child
        if subject is not None:
            scope["subject"] = subject

        state = self._active_state
        if state is not None:
            return self._render_recursive(content, scope, state)

        state = _RecursiveRenderState()
        self._active_state = state
        try:
            return self._render_recursive(content, scope, state)
        finally:
            self._active_state = None

    def render_child(
        self,
        content: str,
        subject: object,
        *,
        source: object | None = None,
        bindings: Mapping[str, object] | None = None,
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

    def _render_recursive(
        self,
        content: str,
        scope: Scope,
        state: _RecursiveRenderState,
    ) -> str:
        current = content
        templates: list[str] = []
        outputs: list[str] = []

        try:
            while True:
                if len(state.templates) >= self.max_depth:
                    raise RecursiveRenderError(
                        f"Recursive template exceeded maximum depth ({self.max_depth})",
                    )
                if current in state.templates:
                    raise RecursiveRenderError("Recursive template cycle detected")
                state.templates.add(current)
                templates.append(current)

                template = self.environment.from_string(
                    current,
                    template_class=RecursiveTemplate,
                )
                rendered = template.render_once(scope).strip()
                if not _contains_template_syntax(rendered, self.environment):
                    return rendered
                if rendered in state.outputs:
                    raise RecursiveRenderError("Recursive template produced repeated output")
                state.outputs.add(rendered)
                outputs.append(rendered)
                current = rendered
        finally:
            for template in templates:
                state.templates.remove(template)
            for output in outputs:
                state.outputs.remove(output)


def render_text(
    content: str,
    *,
    ctx: VmPhaseCtx,
    source: object | None = None,
    subject: object | None = None,
    discourse: Scope | None = None,
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


def _contains_template_syntax(content: str, environment: jinja2.Environment) -> bool:
    return any(
        delimiter in content
        for delimiter in (
            environment.variable_start_string,
            environment.block_start_string,
            environment.comment_start_string,
        )
    )


__all__ = ["RecursiveRenderError", "TextRenderSession", "render_text"]
