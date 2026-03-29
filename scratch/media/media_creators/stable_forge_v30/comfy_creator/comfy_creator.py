from tangl.type_hints import StringMap
from tangl.story import StoryNode
from tangl.media.type_hints import Image
from tangl.media.media_spec import MediaCreationHandler, MediaTemplate
from tangl.media.images.image_spec import ImageSpec
from .comfy_template import ComfyTemplate

class ComfyApi:

    def __init__(self, url):
        self.url = url

    def load_images(self, ims: list[Image]):
        # check if image exists, else load it
        ...

    def execute_pipeline(self, pipeline: StringMap):
        ...

class ComfyHandler(MediaCreationHandler):

    @classmethod
    def _realize_media_config(cls,
                              media_template: ComfyTemplate,
                              reference_node: StoryNode,
                              **kwargs) -> StringMap:
        reference_images = reference_node.get_media_reference_images()
        return {
            'pipeline': media_template.pipeline,
            'reference_images': {x.name: x for x in reference_images}
        }

    @classmethod
    def _call_media_creator(cls, pipeline, reference_images) -> Image:
        api = ComfyApi()
        api.load_images(reference_images)
        image = api.run_pipeline(pipeline)
        return image


