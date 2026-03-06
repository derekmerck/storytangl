"""
Pure text rendering for story content.

StoryTangl renders in two stages:

1) Text transform (this module): template + namespace → plain text. No dispatch, no fragments.
2) Fragment wrapping (node classes): text → BaseFragment with metadata in JOURNAL.

Why
----
Keep template logic testable and swappable (Jinja2 today, markdown/DSL tomorrow) while
leaving fragment/shaping to the domain layer.

Usage
------
- Direct:
  >>> ContentRenderer().render_str("Hello {{ name }}", ns={"name": "World"})
  'Hello World'

- With VM context (uses ctx.get_ns(node) and optional ctx.render_env):
  >>> ContentRenderer.render_with_ctx("{{ hero.name }}", node=block, ctx=ctx)

See also
--------
- :class:`tangl.story.episode.Block` – wraps rendered text as fragments
- :class:`tangl.story.concepts.Concept` – concept fragments
- :class:`tangl.vm.context.Context` – namespace and renderer config
"""
from __future__ import annotations
from typing import Type, Self
from dataclasses import dataclass, field

import jinja2

from tangl.core import GraphItem

@dataclass
class ContentRenderer:
    """
    ContentRenderer(env: jinja2.Environment = ..., templ_cls: Type[jinja2.Template] = ...)

    Pure template-to-text renderer (no dispatch, no fragments).

    Key features
    ------------
    - Stateless: `render_str` is a pure transformation.
    - Context integration: `render_with_ctx` pulls ns via `ctx.get_ns(node)`.
    - Pluggable: supply custom `env`/`templ_cls`; use `from_context` to read `ctx.render_env`.

    Examples
    --------
    >>> r = ContentRenderer()
    >>> r.render_str("{{ n }}x", ns={"n": 3})
    '3x'
    """

    env: jinja2.Environment = field(default_factory=jinja2.Environment)
    templ_cls: Type[jinja2.Template] = jinja2.Template

    @classmethod
    def from_context(cls, ctx) -> Self:
        """
        Create a renderer using optional context config.

        Reads `ctx.render_env` and `ctx.render_templ_cls` if present; falls back to defaults.

        Returns
        -------
        ContentRenderer
        """
        attrs = {}
        if getattr(ctx, "render_env", None) is not None:
            attrs.setdefault("env", ctx.render_env)
        if getattr(ctx, "render_templ_cls", None) is not None:
            attrs.setdefault("templ_cls", ctx.render_templ_cls)
        return cls(**attrs)

    def render_str(self, s: str, *, ns: dict = None, **locals_) -> str:
        """
        Render a template string with a namespace.

        Parameters
        ----------
        s : str
        ns : dict | None
            Template globals (defaults to `{}`).
        **locals_ :
            Local overrides (precedence over `ns`).

        Returns
        -------
        str
        """
        ns = ns or {}
        templ = self.env.from_string(s, template_class=self.templ_cls, globals=ns)
        return templ.render(**locals_)

    @classmethod
    def render_with_ctx(cls, s: str, node: GraphItem, *, ctx, **locals_) -> str:
        """
        Render using a VM Context.

        Uses `from_context(ctx)` and `ctx.get_ns(node)` to render `s` with locals overrides.

        Returns
        -------
        str
        """
        renderer = cls.from_context(ctx)
        s = renderer.render_str(s, ns=ctx.get_ns(node), **locals_)
        return s
