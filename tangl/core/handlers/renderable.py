from __future__ import annotations
from typing import ClassVar, Mapping
import logging

import jinja2

from .task_handler import TaskPipeline, PipelineStrategy
from tangl.core.handlers.has_context import HasContext

logger = logging.getLogger(__name__)

def setup_on_render_pipeline() -> TaskPipeline[Renderable, Mapping]:
    if pipeline := TaskPipeline.get_instance(label="on_render"):
        pass
    else:
        pipeline = TaskPipeline(label="on_render", pipeline_strategy=PipelineStrategy.GATHER)

    return pipeline

# todo: can't invoke this directly b/c it requires context
on_render = setup_on_render_pipeline()

class Renderable(HasContext):

    text: str = None
    jinja_env: ClassVar[jinja2.Environment] = jinja2.Environment()

    @classmethod
    def render_str(cls, s: str, env: jinja2.Environment = None, **context) -> str:
        if not s:
            return ""
        if not env:
            env = cls.jinja_env
        templ = env.from_string(s)
        logger.debug(f'rendering {s} with {context}')
        return templ.render(**context)

    @on_render.register()
    def _provide_label_and_text(self, **context):
        return {
            'label': self.label,
            'text': self.render_str(self.text, **context)
        }

    def render(self):
        context = self.gather_context()
        return on_render.execute(self, **context)
