

from __future__ import annotations
import sys
from typing import *
from pathlib import Path

import attr

from tangl.utils.text_ansi_utils import svg2ansi
from tangl.utils.type_vars import Uid, Svg
from tangl.utils.singleton import Singletons
from tangl.core import StoryNode, Renderable, Traversable
from tangl.story import Scene, Hub
from tangl.story.activity import ActivityHub
from tangl.actor.enums import Gens
from tangl.svgforge.svg_factory import SvgFactory as SvgForge, SvgDesc
from .context_manager import StoryContextManager as Context
from old.world.loader2 import WorldLoader


@attr.define
class World(Singletons):
    _instances: ClassVar[dict] = dict()
    uid: Uid = None

    base_path: Path = None
    label: str = None
    info: Dict = None

    def get_info(self) -> dict:
        """Get the world info spec"""
        return self.info

    entry: str = None

    ui_config: Dict = attr.ib( factory=dict )  #: icon map, color map, etc.
    pwl: str = None  #: Personal word-list for spell checking
    #: Dedicated :class:\`~tangl.svgforge.SvgForge\` singleton
    scene_art: SvgForge = attr.ib( default=None )

    def get_scene_art(self, path: str, fmt: str = "svg") -> Svg | None:
        if self.scene_art is None or not path:
            return
        try:
            grp_uid, im_uid = path.split("/")
        except ValueError as e:  # pragma: no cover
            print( f"Missing resource for {path}", e )
            raise

        if grp_uid == "media":
            fn = self.base_path / "media" / im_uid
            with open( fn, 'rb' ) as f:
                data = f.read()
                return data

        svg_desc = SvgDesc(shapes=[f"{grp_uid}.{im_uid}"])
        svg = self.scene_art.create_collection_svg(svg_desc)
        if fmt == "svg":
            res = SvgForge.to_str(svg)
        elif fmt == "png":
            res = SvgForge.to_png(svg)
        elif fmt == "ansi":
            res = svg2ansi(svg)
        else:
            raise TypeError
        return res

    def get_resource_art(self, obj: Renderable, fmt="svg") -> Svg:
        if hasattr( obj, "get_image"):
            return obj.get_image(fmt=fmt)
        raise NotImplementedError( f"No image hook for {obj}" )

    def __attrs_post_init__(self):
        try:
            super().__attrs_post_init__()  # Singleton init
        except AttributeError:
            pass
        self._init_world()

    _cls_template_maps: dict[str, dict[str, dict]] = attr.ib( factory=dict )
    def get_template(self, cls: type[StoryNode] | str, key: str):
        if isinstance( cls, type ):
            cls = cls.__name__
        return self._cls_template_maps.get(cls, {}).get(key)

    _class_map: dict[str, type[StoryNode]] = attr.ib( factory=dict )
    def get_class(self, cls: str | type[StoryNode]):
        if isinstance( cls, type ):
            cls = cls.__name__
        return self._class_map.get( cls )

    #: classes to instantiate in a new collection
    _new_collection_classes: List[type[StoryNode]] = attr.ib(factory=lambda: [Scene, Hub, ActivityHub])

    def new_context(self, globals: dict = None, **kwargs) -> ContextManager:
        ctx = Context(world=self, **kwargs)
        self._init_context(ctx)  # adds globals, meta
        if globals:
            ctx.globals |= globals
        for k in self._new_collection_classes:
            # strict get, no base classes
            for vv in self._cls_template_maps.get(k.__name__, {}).values():
                try:
                    obj = k(**vv, context=ctx)
                    assert obj.pid in ctx
                except (TypeError, AttributeError, AssertionError) as e:
                    print( vv )
                    raise

        # story els should be stable but may change size bc of actions, stock, etc
        items = list( ctx.values() )
        for item in items:
            # cast references and create other links
            self.init_node( item )
        ctx.mark = ctx[self.entry]

        return ctx

    def ns(self, **kwargs):
        try:
            _ns = super().ns(**kwargs)
        except AttributeError:  # pragma: no cover
            _ns = {}
        try:
            _ns |= {
                'SPAN': self.ui_config['spans'],
                'S': self.ui_config['spans'],
                'ICON': self.ui_config['icons'],
                'Gens': Gens,
                'G': Gens
            }
        except KeyError:
            pass
        _ns |= self._world_ns(**kwargs)
        return _ns

    # Call world module hook

    def _init_world(self):
        try:
            sys.modules[self.uid].__init_world__(self)
        except KeyError:
            pass

    def _init_context(self, ctx: ContextManager):
        try:
            sys.modules[self.uid].__init_context__(ctx)
            meta_defaults = {
                "achievements": set(),
                "plays": 0
            }
            ctx.meta = meta_defaults | ctx.meta
        except KeyError:
            pass

    def init_node(self, obj: StoryNode):
        if hasattr(obj, "__init_node__"):
            obj.__init_node__()
        try:
            sys.modules[self.uid].__init_node__(obj)
        except KeyError:
            pass

    def _world_ns(self, **kwargs) -> dict:
        try:
            return sys.modules[self.uid].__ns__(**kwargs)
        except KeyError:
            return {}

    def done(self, obj: Traversable):
        try:
            sys.modules[self.uid].__done__(obj)
        except KeyError:
            pass

    def status(self, ctx: ContextManager) -> list[dict]:
        try:
            return sys.modules[self.uid].__status__(ctx)
        except KeyError:
            return []

    load = WorldLoader.load
    load_all = WorldLoader.load_all
