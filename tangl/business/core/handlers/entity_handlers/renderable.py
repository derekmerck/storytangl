"""
renderable.py

Defines the :func:`on_render` pipeline for rendering content from a
:class:`Renderable` entity, potentially utilizing Jinja2 templates.
This pipeline depends on (or at least benefits from) the 'gather_context'
pipeline provided by :class:`HasContext`.
"""

from __future__ import annotations
from typing import ClassVar, Mapping
import logging

import jinja2

from tangl.type_hints import StringMap
from tangl.business.core.handlers import TaskPipeline, PipelineStrategy
from .has_context import HasContext

logger = logging.getLogger(__name__)

on_render = TaskPipeline[HasContext, dict](
            label="on_render",
            pipeline_strategy=PipelineStrategy.GATHER
        )
"""
The global pipeline for rendering. Handlers for rendering
should decorate methods with ``@on_render.register(...)``.
"""

class Renderable(HasContext):
    """
    An entity that can produce rendered output (text, HTML, etc.)
    via Jinja2 templates, or other mechanisms. Inherits
    :class:`HasContext` so it can also gather context from a parent
    or graph.

    **Design Overview**:
      - :meth:`render` merges any user-supplied context with
        :meth:`gather_context`.
      - The pipeline :attr:`on_render` is set to
        :attr:`PipelineStrategy.GATHER`, so multiple handlers can
        combine partial rendering data.
      - By default, this class registers a single handler
        (:meth:`_provide_label_and_text`) that returns a dict with
        label and rendered text.

    :ivar text: Optional text or template source to render.
    :type text: str
    :cvar jinja_env: A class-level :class:`jinja2.Environment` used
                     for template rendering if none is explicitly
                     provided.
    :type jinja_env: ClassVar[jinja2.Environment]
    """
    text: str = None
    jinja_env: ClassVar[jinja2.Environment] = jinja2.Environment()

    @classmethod
    def render_str(cls, s: str, env: jinja2.Environment = None, **context) -> str:
        """
        Render a string as a Jinja2 template using the given environment
        and context.

        :param s: The source string/template to render.
        :type s: str
        :param env: A Jinja2 environment to compile the template with.
                    If None, uses :attr:`jinja_env`.
        :type env: jinja2.Environment | None
        :param context: Variables passed to the template rendering.
        :return: Rendered text.
        :rtype: str
        """
        if not s:
            return ""
        if not env:
            env = cls.jinja_env
        templ = env.from_string(s)
        logger.debug(f'rendering {s} with {context}')
        return templ.render(**context)

    @on_render.register()
    def _provide_label_and_text(self, **context) -> StringMap:
        """
        A default rendering handler that includes the entity's label
        and a Jinja2-rendered version of :attr:`text`.

        :param context: Arbitrary data merged by the pipeline.
        :return: A dictionary with keys ``"label"`` and ``"text"``.
        :rtype: dict[str, Any]
        """
        return {
            'label': self.label,
            'text': self.render_str(self.text, **context)
        }

    def render(self, **context) -> StringMap:
        """
        Invoke the :func:`on_render` pipeline for this entity,
        gathering or merging any partial rendering data from
        registered handlers.

        If no context is provided, automatically falls back to
        :meth:`gather_context`.

        :param context: Extra data for the rendering process.
        :return: The merged result from the pipeline. Typically, a list
                 or dict, depending on the pipeline's strategy and
                 the types returned by handlers.
        """
        context = context or self.gather_context()
        return on_render.execute(self, **context)
