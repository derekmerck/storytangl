import logging
from logging import getLogger
from typing import Mapping, Type, Optional
import random

from pydantic import BaseModel
import jinja2

from tangl.utils.response_models import StyleHints
from tangl.utils.safe_builtins import safe_builtins
from tangl.lang.pronoun import Pronoun
from tangl.entity.base_handler import BaseEntityHandler
from tangl.entity.entity import EntityType
from .namespace import NamespaceHandler

logger = getLogger("tangl.render")
logger.setLevel(logging.WARNING)

class RenderHandler(BaseEntityHandler):
    """
    Specialized handler for managing entity text content output.

    It provides functionality to render entities using Jinja2 templates.

    Key Features:
      - `render(entity)`: Compiles and renders entity attributes into a displayable format.
    """
    default_strategy_annotation = "render_strategy"

    # todo: should probably move this into 'World' and found in cls.render(), so
    #       it can be customized for world-specific voices
    default_j2_env = jinja2.Environment()
    Pronoun.register_pronoun_filters(default_j2_env)

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
        env = env or cls.default_j2_env
        ns = ns or {}
        logger.debug( f"templ: {s}, ns = {ns}" )
        try:
            templ = env.from_string(s, globals={'random': random, '__builtins__': safe_builtins}, template_class=template_cls)
            res = templ.render(ns)
            return res
        except TypeError as e:  # pragma: no cover
            logger.critical(f"Failed to render str with type error {s}")
            logger.critical(f"ns keys: {ns.keys()}")
            raise
        except (jinja2.exceptions.TemplateSyntaxError, jinja2.exceptions.UndefinedError) as e:  # pragma: no cover
            logger.critical(f"Failed to render str with syntax error: {s}")
            raise
        except (jinja2.exceptions.UndefinedError, NotImplementedError) as e:  # pragma: no cover
            logger.critical(f"Failed to render str with general error: {s}")
            raise


    @classmethod
    def render(cls, node: EntityType) -> dict:

        # gather fields to render
        try:
            res = cls.invoke_strategies(node, result_handler='merge')
        except Exception as e:
            logger.error(f"Error gathering render fields {node}: {e}")
            return {}

        rendered = {}
        ns = NamespaceHandler.get_namespace(node)
        if hasattr(node, "j2_template_cls"):
            # does the node have its own template?
            template_cls = node.j2_template_cls
        else:
            template_cls = None
        # print( ns )
        for k, v in res.items():
            if not v:
                continue
            elif isinstance(v, str):
                rendered[k] = cls.render_str(v, ns, template_cls=template_cls)
            elif isinstance(v, list) and isinstance( v[0], str ):
                rendered[k] = [cls.render_str(vv, ns, template_cls=template_cls) for vv in v]
            else:
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

    text: Optional[str] = None
    icon: Optional[str] = None

    @RenderHandler.strategy
    def _include_renderable_fields(self) -> dict:
        return {
            'uid': self.uid,
            'text': self.text,
            'icon': self.icon
        }

    @RenderHandler.strategy
    def _include_style_hints(self) -> dict:
        if isinstance(self, StyleHints):
            return {
                'style_id': self.style_id,
                'style_cls': self.style_cls,
                'style_dict': self.style_dict
            }

    def render(self: EntityType) -> dict:
        """
        Render the entity using the RenderHandler.

        :return: A mapping of rendered data.
        """
        return RenderHandler.render(self)
