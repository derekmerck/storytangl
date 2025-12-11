import pathlib
from pathlib import Path
from typing import *
import types

import attr

from tangl.entity import Entity, EntityFactory
from tangl.entity.protocols import Uid
from tangl.entity.factory import EntityType
from tangl.scene import Scene
from .context import Context
from tangl.utils.jinja_filters import Spans, Bunch
from tangl.svg import SvgFactory
from tangl.svg.svg_factory import SvgDesc
from tangl.utils.singleton import Singletons, SingletonsManager
from tangl.utils.text_ansi_utils import svg2ansi

@attr.define
class World( Singletons ):
    """World(*args, **kwargs)"""

    uid: str = attr.ib( default=None, validator=attr.validators.instance_of(str))
    _instances: ClassVar = dict()  # singleton subclasses should have their own map

    label: str = None
    info: Dict[str, str] = attr.Factory( factory=dict )
    entry: Uid = "main_menu/start"

    # UI properties
    spans: Spans = attr.ib( converter=Spans, factory=dict )
    icons: Bunch = attr.ib( converter=Bunch, factory=dict )

    scene_art: 'SvgFactory' = None
    pwl: str = None  # Every world could have a unique pwl
    hooks: types.ModuleType = attr.ib( default=None )

    base_path: Path = None
    media_dir: Path = Path("media")
    @property
    def media_path(self) -> Path:
        return self.base_path / self.media_dir

    entity_factory: EntityFactory = attr.ib( factory=EntityFactory )
    asset_manager: SingletonsManager = attr.ib( factory=SingletonsManager )

    def __attrs_post_init__(self):
        super().__attrs_post_init__()  # registers the singleton
        self._init_world()             # Manually override base classes, add templates and funcs

    def get_info(self):
        return self.info

    def get_scene_art(self, path: Uid, fmt: str = "svg") -> Optional[Union[str, bytes]]:
        if self.scene_art is None:
            return
        grp_uid, im_uid = path.split("/")

        if grp_uid == "media":
            fn = self.media_path / im_uid
            with open( fn, 'rb' ) as f:
                data = f.read()
                return data

        svg_desc = SvgDesc(shapes=[f"{grp_uid}.{im_uid}"])
        svg = self.scene_art.create_collection_svg(svg_desc)
        if fmt == "svg":
            res = SvgFactory.to_str(svg)
        elif fmt == "png":
            res = SvgFactory.to_png(svg)
        elif fmt == "ansi":
            res = svg2ansi(svg)
        else:
            raise TypeError
        return res


    #######################
    # Client and Entity Management
    #######################

    init_for_ctx: list[str] = ["Scene", "Hub"]

    def new_ctx(self, **kwargs):
        if "globals" in kwargs:
            _gl = self._init_globals() | kwargs.pop('globals')
        else:
            _gl = self._init_globals()
        ctx = Context( world=self, globals=_gl, meta=self._init_meta(), **kwargs )
        for k in self.entity_factory.templates.keys():
            if k[0] in self.init_for_ctx:
                # scene create casts all template roles
                self.new_entity( k[0], uid=k[1], ctx=ctx )

        # alternatively, this could be done by iterating over all objects in the context
        # but it would either exclude anything not registered, or require checking children
        # to see if they are registered before descending...
        for sc in ctx.get_scenes():
            self._init_entity(sc)

        return ctx

    # Note there are 2 places where ctx can create entities:
    # - actor.role.templ
    # - asset.stock.templ
    # Need to ensure they call world._init_entity as well
    def new_entity(self, entity_typ: str, **kwargs) -> EntityType:
        """This is particularly for creating entities without calling the cls directly"""
        return self.entity_factory.new_entity(entity_typ, **kwargs)

    # def new_scene(self, *args, **kwargs) -> Scene:
    #     return self.new_entity("Scene", *args, **kwargs)  # type: Scene

    # def new_actor(self, *args, **kwargs) -> Actor:
    #     return self.new_entity("Actor", *args, **kwargs)  # type: Actor

    def ns(self, ctx: Context = None, **kwargs) -> dict:
        _ns = {}
        _ns |= {'SPAN': self.spans,
                'S': self.spans,
                'ICON': self.icons }
        _ns |= self._world_ns( ctx=ctx )
        return _ns

    def get_resource_art(self, obj: Entity, fmt="svg"):
        from tangl.31.actor.avatar import Avatar
        if isinstance( obj, Avatar ):
            return obj.get_avatar()
        raise NotImplementedError( f"No im for {obj}" )

    def get_asset(self, uid: str ) -> 'AssetType':
        return self.asset_manager.instance( uid )


    #######################
    # Hooks
    #######################

    ignore_missing_hooks: bool = False

    def _init_world(self):                 # called in __attr_post_init__
        try:
            self.hooks.__init_world__(self)
        except AttributeError:
            if not self.ignore_missing_hooks:
                raise NotImplementedError

    def _init_globals(self) -> Dict:       # called by new_ctx
        res = {
            'turn': 1,
            'mark': self.entry
        }
        try:
            res |= self.hooks.__init_globals__()
        except AttributeError:
            if not self.ignore_missing_hooks:
                raise NotImplementedError
        return res

    def _init_meta(self) -> Dict:            # called by new_ctx
        res = {
            'plays': 0,
            'total_turns': 0,
            'achievements': set(),
        }
        try:
            res |= self.hooks.__init_meta__()
        except AttributeError:
            if not self.ignore_missing_hooks:
                raise NotImplementedError
        return res

    def _world_ns(self, ctx: Context = None) -> Dict:  # called by ctx.ns()
        try:
            return self.hooks.__ns__( ctx=ctx )
        except AttributeError:
            if not self.ignore_missing_hooks:
                raise NotImplementedError
            return {}

    def _finalize_ctx(self, ctx) -> Context:  # called by new_ctx
        ctx.meta['plays'] += 1
        ctx.meta['total_turns'] += ctx.globals['turns']
        try:
            self.hooks.__finalize_ctx__(ctx)
        except AttributeError:
            if not self.ignore_missing_hooks:
                raise NotImplementedError

    def _init_entity(self, obj: Entity):   # called in new_scene and new_actor
        if hasattr( obj, "__init_entity__"):
            obj.__init_entity__()
        try:
            self.hooks.__init_entity__(obj)
        except AttributeError:
            if not self.ignore_missing_hooks:
                raise NotImplementedError

    def done(self, obj: Scene):       # called by API on the scene container when a choice is marked "done"

        if hasattr(obj, "visit"):
            obj.visit()

        try:
            self.hooks.__done__(obj)
        except AttributeError as e:
            if not self.ignore_missing_hooks:
                raise NotImplementedError( e )
            if hasattr(obj.ctx, "turn"):
                obj.ctx.turn += 1

    def get_status(self, ctx: Context) -> list[dict]:  # called by API for status update
        try:
            return self.hooks.__get_status__(ctx)
        except AttributeError:
            if not self.ignore_missing_hooks:
                raise NotImplementedError
            return []
