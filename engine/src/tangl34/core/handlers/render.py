import logging
from typing import ClassVar, Self

import jinja2

from ..type_hints import Context, StringMap
from ..journal import ContentFragment
from ..entity import Entity
from .enums import ServiceKind
from .base import handler
from .context import HasContext

logger = logging.getLogger(__name__)

# todo: Template engine swappability: Let Renderable accept a template_engine parameter, so users can drop in their own (e.g., string.Template, Mako) with no code change.

class Renderable(HasContext):
    content: str = None
    jinja_env: ClassVar[jinja2.Environment] = jinja2.Environment()

    @classmethod
    def render_str(cls, s: str, *, ctx: Context, env: jinja2.Environment = None) -> str:
        """
        Render a string as a Jinja2 template using the given environment
        and context.

        :param s: The source string/template to render.
        :type s: str
        :param ctx: Variables passed to the template rendering.
        :param env: A Jinja2 environment to compile the template with.
                    If None, uses :attr:`jinja_env`.
        :type env: jinja2.Environment | None
        :return: Rendered text.
        :rtype: str
        """
        if not s:
            return ""
        if not env:
            env = cls.jinja_env
        templ = env.from_string(s)
        logger.debug(f'rendering {s} with {ctx}')
        return templ.render(ctx)

    @handler(ServiceKind.RENDER)
    def _provide_label_and_text(self: Entity | Self, ctx) -> list[StringMap]:
        """
        A default rendering handler that includes the entity's label
        and a Jinja2-rendered version of :attr:`content`.

        :param ctx: Arbitrary data merged by the pipeline.
        :return: A dictionary with keys ``"label"`` and ``"content"``.
        :rtype: dict[str, Any]
        """
        return [{
            'label': self.label,
            'content': self.render_str(self.content, ctx=ctx)
        }]

    @staticmethod
    def render_handler(priority=10, caller_criteria=None):
        return handler(ServiceKind.RENDER, priority=priority, caller_criteria=caller_criteria)

    @classmethod
    def render_content(cls, caller, *objects, ctx) -> list[ContentFragment]:
        logger.debug("rendering content")
        fragments = []  # type: list[ContentFragment]
        for h in cls.gather_handlers(ServiceKind.RENDER, caller, *objects, ctx=ctx):
            logger.debug(f"Calling: {h!r}")
            fragments.extend(h.func(caller, ctx))
        return [ContentFragment.structure(data) for data in fragments]


