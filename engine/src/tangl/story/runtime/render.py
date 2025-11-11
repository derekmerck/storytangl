from __future__ import annotations
from typing import Type, Self
from dataclasses import dataclass, field

import jinja2

from tangl.core import GraphItem

@dataclass
class ContentRenderer:
    """
    Lots of things can render their content, but only blocks surface
    'on_journal' tasks for dispatch -- b/c only blocks can be cursors.

    Other graph items can provide fragments to blocks on request, usually
    labelled with a function name like '<type>_fragment'.

    Using _ContentRenderer_ does not go through dispatch, it requires only
    a ns, optional env and template class, and it produces text.

    However, it includes a helper class that can extract env, template class,
    and ns from a context, if available.
    """

    env: jinja2.Environment = field(default_factory=jinja2.Environment)
    templ_cls: Type[jinja2.Template] = jinja2.Template

    @classmethod
    def from_context(cls, ctx) -> Self:
        attrs = {}
        if getattr(ctx, "render_env", None) is not None:
            attrs.setdefault("env", ctx.render_env)
        if getattr(ctx, "render_templ_cls", None) is not None:
            attrs.setdefault("templ_cls", ctx.render_templ_cls)
        return cls(**attrs)

    def render_str(self, s: str, *, ns: dict = None, **locals_) -> str:
        ns = ns or {}
        templ = self.env.from_string(s, template_class=self.templ_cls, globals=ns)
        return templ.render(**locals_)

    @classmethod
    def render_with_ctx(cls, s: str, node: GraphItem, *, ctx, **locals_) -> str:
        renderer = cls.from_context(ctx)
        s = renderer.render_str(s, ns=ctx.get_ns(node), **locals_)
        return s
