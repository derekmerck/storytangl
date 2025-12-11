from copy import deepcopy
from typing import Mapping
from collections import ChainMap
from importlib import resources as resources_

import attr
import pluggy
import jinja2

from tangl.data_models import Uid, InfoResponse
from tangl.utils.singletons import Singletons
from tangl.utils.measure import Measure
from tangl.story.story import Story
from tangl.story.scene import Scene
from tangl.story.actor import Actor
from tangl.user import User

from .story_plugin_spec import StoryPluginSpec
from .default_story_plugin import DefaultStoryPlugin
from pathlib import Path

@attr.s(hash=False)
class World(Singletons):
    """
    Manages the creation and configuration of a specific story type.

    The story manager loads templates and provides methods to create scenes and the overall story.
    """

    uid: Uid = attr.ib()

    #: dictionary of scene and other story-node templates (kwargs), keyed by scene_uid
    story_templates: dict = attr.ib(factory=dict)
    unique_block_ids: bool = True

    # todo: should change node creation to support a text-reference
    #       instead of the actual text.  A text-reference triggers
    #       a request back to the world to look for the localized
    #       text given the user or engine locale.

    #: independent pluggy plugin manager per world instance
    pm = attr.ib(init=False)
    @pm.default
    def _mk_pm(self):
        pm = pluggy.PluginManager("story")
        pm.add_hookspecs(StoryPluginSpec)
        pm.register(DefaultStoryPlugin(), "default")
        return pm

    locals: dict = attr.ib(factory=dict)

    def ns(self) -> Mapping:
        maps = self.pm.hook.on_get_world_ns(world=self)
        maps.extend([ self.locals, Measure.member_map() ])
        res = ChainMap(*maps)
        return res

    info: InfoResponse = attr.ib(factory=dict)
    def get_world_info(self) -> InfoResponse:
        return self.info

    media_resource_module: str = attr.ib( default=None )
    media_resource_dir: str | Path = attr.ib( default=None )

    def media_subdir(self, fn):
        p = Path(fn)
        match p.suffix:
            case ".svg":
                return "svg"
            case ".png" | "webp":
                return "images"
            case "mp3":
                return "audio"

    def media_filepath(self, fn: str | Path):
        if self.media_resource_module:
            module_ = self.media_resource_module + '.' + self.media_subdir(fn)
            p = resources_.path(module_, fn)
        elif self.media_resource_dir:
            p = Path(self.media_resource_dir) / fn
        if p.is_file():
            return p
        raise FileNotFoundError(f"No such file {p}")

    def media_data(self, fn: str | Path, binary=True):
        f = None
        if self.media_resource_module:
            if binary:
                f = resources_.open_binary(self.media_resource_module, fn)
            else:
                f = resources_.open_text(self.media_resource_module, fn)
        elif self.media_resource_dir:
            p = Path(self.media_resource_dir) / fn
            if p.is_file():
                if binary:
                    f = open( p, 'rb' )
                else:
                    f = open( p, 'r' )
        if f:
            return f
        raise FileNotFoundError

    def get_media(self,
                  fn = None,       # filename
                  as_path = True,  # return a file path rather than a data handle
                  **kwargs):
        # todo: just returns a path if it's a legit file
        if fn and as_path:
            return self.media_filepath( fn )

    def create_story(self, user: User = None, **kwargs) -> Story:

        StoryClass = self.pm.hook.on_new_story(cls=Story)[-1]
        new_story = StoryClass(world=self, user=user, locals=kwargs)

        story_templates = deepcopy(self.story_templates)
        # todo, this should be for all story templates?  Or just scenes?

        actors = story_templates.get('actors', [])

        # Sometimes story templates are dicts of { uid: data, ... }, sometimes just [data,..]
        if isinstance(actors, dict):
            actors = actors.values()
        for actor_data in actors:
            actor_data['index'] = new_story
            a = Actor.from_dict(actor_data)

        scenes = story_templates.get('scenes', [])

        # Sometimes story templates are dicts of { uid: data, ... }, sometimes just [data,..]
        if isinstance(scenes, dict):
            scenes = scenes.values()
        for scene_data in scenes:
            # print(scene_data)
            scene_data['index'] = new_story
            Scene.from_dict(scene_data)

        new_story.enter()
        return new_story

    def load_story_templates(self, **kwargs):
        story_templates_results = self.pm.hook.on_load_story_templates(kwargs=kwargs)  # type: list[dict]
        for story_templates in story_templates_results:
            self.story_templates.update( story_templates )
        # from pprint import pprint
        # pprint(self.story_templates, width=110, sort_dicts=False)
    #
    # def on_new_node(self, cls):
    #     return self.pm.hook.on_new_node(cls=cls)[0]

    jinja_env_cls: jinja2.Environment = jinja2.Environment

    def __attrs_post_init__(self):
        self.jinja_env = self.jinja_env_cls()
        self.pm.hook.on_init_world(world=self)
