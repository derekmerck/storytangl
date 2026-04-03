from typing import Self
import json
from copy import deepcopy

from tangl.type_hints import StringMap
from tangl.core.entity import Entity
from tangl.media.media_spec import MediaTemplate

class ComfyTemplate(MediaTemplate):

    pipeline: StringMap = None

    def realize_template(self, ref: Entity) -> Self:
        pipeline = deepcopy(self.pipeline)
        # todo: deep scan the copy of pipeline, render any fields with {{ as
        #       jinja templates with ref=ref
        return ComfyTemplate(pipeline=pipeline)

    def as_json(self):
        return json.dumps(self.pipeline)

    @classmethod
    def from_json(cls, data: str) -> Self:
        pipeline = json.loads(data)
        return ComfyTemplate(pipeline=pipeline)


