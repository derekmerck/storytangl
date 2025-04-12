from __future__ import annotations
import logging
from typing import Mapping, Type, Optional, Any
import random

from pydantic import BaseModel, Field
import jinja2

from tangl.type_hints import UniqueLabel
from tangl.utils.safe_builtins import safe_builtins
from tangl.core.handler import BaseHandler, Priority
from .namespace import NamespaceHandler

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)

class RenderHandler(BaseHandler):
    """
    Specialized handler for managing entity text content output.

    It provides functionality to render entities using Jinja2 templates.

    Key Features:
      - `render(entity)`: Compiles and renders entity attributes into a displayable format.
    """
    @classmethod
    def j2_env(cls) -> jinja2.Environment:
        return jinja2.Environment()

    @classmethod
    def render_str(cls, s: str,
                   ns: Mapping = None,
                   env: jinja2.Environment = None,
                   template_cls: Type[jinja2.Template] = None):
        """
        Render a string template using Jinja2 with the provided namespace and/or Environment.

        :param s: The template string to be rendered.
        :param ns: A mapping of variables to be used in the template, this can include story-specific callbacks
        :param env: An optional jinja2 environment, this can include additional pre- and post-processors
        :param template_cls: An optional jinja2 template class, this can include additional filters
        :return: The rendered string.
        """
        env = env or cls.j2_env()
        ns = ns or {}
        logger.debug( f"templ: {s}, ns = {ns}" )
        try:
            templ = env.from_string(s, globals={'random': random, '__builtins__': safe_builtins}, template_class=template_cls)
            res = templ.render(ns)
            return res
        except TypeError:  # pragma: no cover
            logger.critical(f"Failed to render str with type error {s}")
            logger.critical(f"ns keys: {ns.keys()}")
            raise
        except (jinja2.exceptions.TemplateSyntaxError, jinja2.exceptions.UndefinedError) as e:  # pragma: no cover
            logger.critical(f"Failed to render str with syntax error: {s}")
            raise
        except (jinja2.exceptions.UndefinedError, NotImplementedError) as e:  # pragma: no cover
            logger.critical(f"Failed to render str with general error: {s}")
            raise

    # @BaseHandler.task_signature
    # def on_render(entity: Renderable, **kwargs) -> Mapping[str, Any]:
    #     ...

    @classmethod
    def strategy(cls, task_id: UniqueLabel = "on_render",
                 domain: UniqueLabel = "global",
                 priority: int = Priority.NORMAL ):
        return BaseHandler.strategy(task_id, domain, priority)

    @classmethod
    def render(cls, entity: Renderable, **kwargs) -> dict:

        # gather raw fields to render
        try:
            raw = cls.execute_task(entity, 'on_render', result_mode='merge', **kwargs)
        except Exception as e:
            logger.error(f"Error gathering render fields {entity}: {e}")
            return {}

        rendered = {}
        ns = NamespaceHandler.get_namespace(entity)
        if hasattr(entity, "j2_template_cls"):
            # does the node have its own template?
            template_cls = entity.j2_template_cls
        else:
            template_cls = None
        # print( ns )
        for k, v in raw.items():
            if not v:
                # discard empty entries
                continue
            elif isinstance(v, str):
                # render strings
                rendered[k] = cls.render_str(v, ns, template_cls=template_cls)
            elif isinstance(v, list) and all( [ isinstance(vv, str) for vv in v ] ):
                # render lists of strings
                rendered[k] = [cls.render_str(vv, ns, template_cls=template_cls) for vv in v]
            elif isinstance(v, dict) and all( [ isinstance(vv, str) for vv in v.values() ] ):
                # render dicts of strings
                rendered[k] = {k: cls.render_str(vv, ns, template_cls=template_cls) for k, vv in v.items()}
            else:
                # pass through non-strings
                rendered[k] = v

        return rendered


class Renderable(BaseModel):
    """
    Facilitates rendering of entities with textual representation, icons, and titles.

    This mixin expects the attached object to have a namespace that can be used during rendering.

    Rendered text is formatted in markdown and will be further reduced to a final display format.

    Key Features:
      - `text`, `icon`: Attributes to store the entity's basic visual/textual representation.
      - `render()`: Compiles the entity's renderable attributes into a displayable format.
    """

    text: Optional[str] = Field(None, json_schema_extra={'instance_var': True})
    icon: Optional[str] = None

    @RenderHandler.strategy()
    def _include_renderable_fields(self, **kwargs) -> Mapping[str, Any]:
        return {
            'uid': self.uid,
            'text': self.text,
            'icon': self.icon
        }

    # @RenderHandler.strategy
    # def _include_style_hints(self) -> dict:
    #     if isinstance(self, StyleHints):
    #         return {
    #             'style_id': self.style_id,
    #             'style_cls': self.style_cls,
    #             'style_dict': self.style_dict
    #         }

    def render(self, **kwargs) -> dict:
        """
        Render the entity using the RenderHandler.

        :return: A mapping of rendered data.
        """
        return RenderHandler.render(self, **kwargs)
