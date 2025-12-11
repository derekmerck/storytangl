# Worlds are semi-singletons.  Look them up with "World.find"
import types

from pathlib import Path
from typing import *

import attr

from tangl.31.entity import Entity, EntityFactory
from tangl.31.scene import Scene, Hub, Action   # Story beats, places
from tangl.31.scene import Challenge, UnitChallenge
from tangl.31.actor import Actor        # Characters
from tangl.31.asset import Asset, Unit  # Chattels, fungibles
from tangl.31.svg import SvgFactory     # Scene art

from tangl.31.utils.singleton import Singletons
from tangl.31.utils.jinja_filters import Spans, Bunch
from tangl.31.svg.svg_factory import SvgDesc

from .loader import WorldLoader
from .context import Game
from .protocols import World as World_


@attr.define
class World(Singletons, WorldLoader, Entity, World_):

    _instances: ClassVar = dict()

    # Setup

    label: str = None
    info: Dict = None

    entry: str = "main_menu/start"
    base_path: Path = None
    backend_ui: Dict = attr.ib(factory=dict)
    hooks: types.ModuleType = None
    scene_art: SvgFactory = None
    pwl: str = None  # Every world could have a unique pwl

    _scene_templs: Dict = attr.ib(repr=False, default=None)
    scenes: EntityFactory = attr.ib(init=False)
    @scenes.default
    def mk_scenes(self):
        """ :meta private: """
        if not self._scene_templs:
            return
        f = EntityFactory(templs=self._scene_templs, bases=Scene)
        return f

    _hub_templs: Dict = attr.ib(repr=False, default=None)
    hubs: EntityFactory = attr.ib(init=False)
    @hubs.default
    def mk_hubs(self):
        """ :meta private: """
        if not self._hub_templs:
            return
        f = EntityFactory(templs=self._hub_templs, bases=Hub)
        return f

    _actor_templs: Dict = attr.ib(repr=False, default=None)
    actors: EntityFactory = attr.ib(init=False)
    @actors.default
    def mk_actors(self):
        """ :meta private: """
        f = EntityFactory(templs=self._actor_templs, bases=Actor)
        return f

    _asset_templs: Dict = attr.ib(repr=False, default=None)
    assets: EntityFactory = attr.ib(init=False)
    @assets.default
    def mk_assets(self):
        """ :meta private: """
        f = EntityFactory(templs=self._asset_templs, bases=Asset)
        return f

    _unit_templs: Dict = attr.ib(repr=False, factory=dict)
    units: Type[Unit] = attr.ib(init=False)
    @units.default
    def mk_unit_registry(self):
        """ :meta private: """
        # make a private instance of the unit class
        units = attr.make_class('Unit', {}, bases=(Unit,))
        units._instances = {}
        for k, v in self._unit_templs.items():
            units( **v )
        return units

    def __attrs_post_init__(self):
        self._instances[self.uid] = self
        f = self.get_hook("__init_world__")
        if f:
            f(self)


    # Service Functions

    def filter_ctx(self, ctx: Game, filt = None):
        if filt:
            res = filter( filt, ctx.entities.values() )
        else:
            res = ctx.entities.values()
        res = list( res )
        return res

    def get_scenes(self, ctx: Game, scene_typ = None):
        if scene_typ:
            filt = lambda x: isinstance(x, Scene) and x.scene_typ == scene_typ
        else:
            filt = lambda x: isinstance(x, Scene)
        res = self.filter_ctx(ctx, filt)
        return res

    def scenes_to_actions(self, ctx: Game, scene_typ = None):
        scenes = self.get_scenes(ctx, scene_typ)
        res = []
        for sc in scenes:
            res.append( Action.from_game_obj( sc ) )
        return res

    def get_scene_art(self, grp_uid: str, im_uid: str, fmt: str = "svg"):
        if self.scene_art is None:
            return
        svg_desc = SvgDesc(shapes=[f"{grp_uid}.{im_uid}"])
        svg = self.scene_art.create_collection_svg(svg_desc)
        if fmt == "svg":
            res = SvgFactory.to_str(svg)
        elif fmt == "png":
            res = SvgFactory.to_png(svg)
        else:
            raise TypeError
        return res


    # Hooking

    def get_hook(self, name) -> Optional[Callable]:
        if hasattr( self.hooks, name ):
            return getattr( self.hooks, name )

    def done(self, obj: Scene):
        f = self.get_hook("__done__")
        if f:
            f( obj )

    def init_globals(self):
        f = self.get_hook("__init_globals__")
        if f:
            res = f()
        else:
            res = {}
        res['turn'] = 0
        return res

    def init_meta(self):
        f = self.get_hook("__init_meta__")
        if f:
            res = f()
        else:
            res = {}
        res['plays'] = 0
        res['achievements'] = set()
        return res

    def finalize_context(self, ctx: 'Game'):
        f = self.get_hook("__finalize_context__")
        if f:
            f( ctx=ctx )

    def get_status(self, ctx: Game):
        f = self.get_hook("__get_status__")
        if f:
            return f(ctx)


    # Ctx and ns related

    def new_ctx(self, meta: Dict = None):

        meta = meta or {}
        if self.uid not in meta:
            meta[self.uid] = self.init_meta()

        ctx = Game(
            world=self,
            meta=meta,
            globals=self.init_globals()
        )
        # Create raw scenes and register them
        for k in self.scenes.keys():
            sc = self.scenes.new_instance(k, ctx_=ctx)
            sc.__entity_init__()
        if self.hubs:
            for k in self.hubs.keys():
                sc = self.hubs.new_instance(k, ctx_=ctx)
                sc.__entity_init__()

        # Generate dynamic content based on stable ctx
        f = self.get_hook("__init_obj__")
        for sc in self.get_scenes(ctx):
            if f:
                f(sc)
                sc._set_parent()
            sc.__entity_init__(stable=True, fresh=True)

        return ctx

    def inflate_ctx(self, data: Dict) -> 'Game':
        ctx = Game(world=self,
                   meta=data.pop("meta", {}),
                   globals=data.pop("globals", {}),)
        for k, v in data.items():
            cls_ = v.pop('cls')
            if cls_ == "Scene":
                obj = self.scenes.inflate_instance(**v, ctx_=ctx)
            if cls_ == "Hub":
                obj = self.hubs.inflate_instance(**v, ctx_=ctx)
            if cls_ == "Actor":
                obj = self.actors.inflate_instance(**v, ctx_=ctx)
            if cls_ == "Asset":
                obj = self.asset.inflate_instance(**v, ctx_=ctx)
            obj.__entity_init__()

        # relink all
        for sc in self.get_scenes(ctx):
            sc.__entity_init__(stable=True)

        return ctx

    def ns(self, _ns: Dict = None):

        f = self.get_hook("__ns__")
        if f:
            _ns = f(_ns)

        _ns['SPAN'] = Spans(self.backend_ui.get("SPAN", {}))
        _ns['S'] = _ns['SPAN']
        _ns['ICON'] = Bunch(self.backend_ui.get("ICON", {}))

        return _ns
