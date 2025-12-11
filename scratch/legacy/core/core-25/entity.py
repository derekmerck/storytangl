
from __future__ import annotations

import functools
import random
import types
from typing import *
import inspect
from numbers import Number

import attr

from .meta import EntityMeta
from .utils import mk_eid

def structure_entity(cls, fields: List[attr.Attribute]):
    """
    - Figure out value:
    -   kwarg?
    -   template value?
    -   default value?
    - Reduce the value if directed
    - Convert the value
    -   if entity or entity-list/dict:
    -      instantiate
    -   elif converter
    -      convert

    Change default to factory reduce( default ) if directed
    Change converter to structure entities( obj ) if type is entity list/dict
    """

    def entity_default(field, self):
        default = self.template_default( field.name )
        if not default:
            default = field.default
        return default

    def entity_converter(field, value):
        """
        1. reduce defaults to a single value
        2. convert children
        3. -
        3. convert non-entity children that are enums or have explicit converters
        """

        funcs = []

        def reduce_default(value):
            return value

        if field.metadata.get("reduce"):
            funcs.append( reduce_default )

        def structure_child(child_cls, **kwargs):
            return child_cls( **kwargs )

        def structure_child_list(child_cls, kwargs_list: list[dict]):
            res = []
            for k in kwargs_list:
                res.append( structure_child(child_cls, **k) )
            return res

        def structure_child_dict(child_cls, kwargs_dict: dict[str, dict]):
            res = {}
            for k, v in kwargs_dict:
                res[k] = structure_child( child_cls, **v )

        if issubclass(field.type, Entity):
            child_cls = field.type
            funcs.append( functools.partial( structure_child, child_cls ) )
        elif hasattr(field.type, "__args__") and issubclass(field.type.__args__[0], Entity):
            child_cls = field.type[0]
            funcs.append( functools.partial( structure_child_list, child_cls ) )
        elif hasattr(field.type, "__args__") and issubclass(field.type.__args__[1], Entity):
            child_cls = field.type[1]
            funcs.append( functools.partial( structure_child_dict, child_cls ) )

        if field.converter is not None:
            funcs.append( field.converter )


def reduce_defaults(cls, fields: List[attr.Attribute]):
    res = []
    for f in fields:
        if f.metadata.get("reduce"):

            if f.converter is not None:
                converter = f.converter
                new_conv = lambda val: converter( Entity._reduce_default( val ))
            else:
                new_conv = lambda val: Entity._reduce_default( val )

            g = f.evolve( converter=new_conv )
            print( "adding reducer" )
            res.append( g )

        else:
            res.append( f )

    return res


@attr.define(init=False, slots=False, kw_only=True, field_transformer=reduce_defaults)
class Entity:
    """Base-class for a self-configuring story node"""

    eid: str = attr.ib( factory=mk_eid )
    meta: EntityMeta = attr.ib( factory=EntityMeta, repr=False )
    parent: Entity | None = attr.ib( default=None, repr=False )

    @property
    def root(self) -> Entity | None:
        _root = self
        while _root.parent:
            _root = _root.parent
        return _root

    #: Optional author-friendly Node-ID, based on story-role
    uid: str | None = None

    @property
    def path(self) -> str:
        """Handle to index a node by uid-path in a context, such as `scene/ro1` or `scene/my_block`"""
        _root = self
        _path = str(_root.uid)
        while _root.parent:
            _root = _root.parent
            _path = str(_root.uid) + "/" + _path
        return _path

    __subclass_map__: ClassVar[dict] = {}

    @classmethod
    def __init_subclass__(cls, **kwargs):
        cls.__subclass_map__[cls.__name__] = cls

    @classmethod
    def __new__(cls, *args, **kwargs):
        """Figure out if the object wants to be structured differently
        than the family-generic type name.

        There are several possibilities here.

        Figure out the _family_

        - assume the family is cls
        - if there is a kwargs['entity_typ_hint'], this is being structured
          as a child; the _family_ is the entity_typ_hint (probably it's the same as cls)
        - if there is a factory override for the family, use that instead
          ie, Scene may have been overridden in kwargs['factory'].class_map

        Figure out the specific subtype

        - Once we know the class family, check to see if there is an explicit
          kwargs[entity_typ], ie, this Block may be a Challenge.  If there is,
          lookup the entity_typ in the family._class_map and use that instead

        - if there is an entity_typ but no such entity_typ in the family._class_map,
          this may be a blind-inflation, so we need to check the base Entity._class_map
        """
        _cls = cls
        for k, v in kwargs.items():
            if k.endswith("_cls"):
                new_cls_name = kwargs.pop( k )  # remove v
                _cls = cls.__subclass_map__.get(new_cls_name)
                print( 'entity.new: New cls', new_cls_name, _cls )
                break
        if attr.has(_cls):
            try:
                attr.resolve_types(_cls)
            except NameError:
                pass
        instance = super().__new__(_cls)
        return instance

    def __init__(self, meta: EntityMeta = None, templates: List = None, **kwargs):
        """
        -- actor only --
        - Check kwargs and templates for pre-template vars (demographics)
        - Create pre-template defaults if necessary
        -- all entities --
        - Create variable defaults
        - Reduce variable defaults
        - Convert all variables to final state
        """
        # discard directions to new
        for k in list( kwargs.keys() ):
            if k.endswith("_cls"):
                kwargs.pop( k )

        if templates and meta:
            defaults = self._template_defaults( templates, meta )
            if defaults:
                kwargs = defaults | kwargs
        if not meta:
            meta = attr.fields_dict( self.__class__ )['meta'].default.factory()
        children = self._structure_children(meta=meta, **kwargs)
        if children:
            kwargs |= children
        self.__attrs_init__(meta=meta, **kwargs)

    def __attrs_post_init__(self):
        try:
            super().__attrs_post_init__()
        except AttributeError:
            pass
            # print( f"No attrs parent from {self.__class__}")

        self.meta.add( self )

    def __init_entity__(self):
        """May be called multiple times before meta is stable"""
        pass

    def _structure_children( self, **kwargs):
        res = {}
        for field in self.__attrs_attrs__:  # type: attrs.Attribute

            if not field.init:
                continue

            if field.name.startswith("_"):
                _fieldname = field.name[1:]
            else:
                _fieldname = field.name

            hint = field.type
            if hasattr(hint, "__mro__") and hint.__mro__[0] in [dict, list]:
                # can't parse the child-type out of 'dict' or 'list' hints
                raise TypeError(f"{self.__class__}.{field.name}: Use 'Dict|List[]' instead of dict|list[] for typing.")

            def _create_child(child_cls, v, uid_ = None):
                # helper func to instantiate new child from str or dict
                if isinstance(v, Entity):
                    # pre-instantiated
                    return v
                if isinstance(v, str):
                    # update v if there is a "consumes_str" flag on a field
                    for field in attr.fields(child_cls):
                        if "consumes_str" in field.metadata:
                            v = {field.name: v}
                            break
                if isinstance(v, dict):
                    if not v.get("uid") and uid_:
                        v["uid"] = uid_
                    el = child_cls(**v, parent=self, meta=kwargs['meta'])
                    return el
                raise TypeError(f"Couldn't transform kwargs into an entity: {kwargs}")

            def _get_field_default() -> Any:
                default = field.default
                if isinstance( default, attr.Factory ):
                    if default.takes_self:
                        # may depend on partially initialized kwargs as "self" in next step
                        _self = {'self': types.SimpleNamespace( **res )}
                        default = default.factory(**_self)
                    else:
                        default = default.factory()
                return default

            value = None
            if hasattr( field.type, "__origin__") and hasattr( field.type, "__args__" ):
                # It's a list or dict
                if field.type.__origin__ == list and issubclass( field.type.__args__[0], Entity ):
                    value = kwargs.get(_fieldname, _get_field_default())
                    child_cls = field.type.__args__[0]
                    res_ = []
                    for i, v in enumerate(value):
                        obj = _create_child( child_cls, v, f"{field.name[0:2]}{i}")
                        res_.append( obj )
                    value = res_
                elif field.type.__origin__ == dict and issubclass( field.type.__args__[1], Entity ):
                    value = kwargs.get(_fieldname, _get_field_default())
                    child_cls = field.type.__args__[1]
                    if not issubclass( child_cls, Entity ):
                        break
                    res_ = {}
                    for k, v in value.items():
                        obj = _create_child( child_cls, v, k )
                        res_[ k ] = obj
                    value = res_
            elif isinstance(value, dict) and\
                    inspect.isclass(field.type) and \
                    issubclass(field.type, Entity):
                value = kwargs.get(_fieldname, _get_field_default())
                child_cls = field.type
                value = _create_child( child_cls, value )
            elif value and isinstance(value, str) and\
                    inspect.isclass(field.type) and \
                    issubclass(field.type, Entity):
                    # look for consumes str
                value = kwargs.get(_fieldname, _get_field_default())
                for field in attr.fields(field.type):
                    if "consumes_str" in field.metadata:
                        value = {field.name: value}
                        break
                child_cls = field.type
                value = _create_child( child_cls, value )
            if value:
                res[_fieldname] = value
        return res

    @staticmethod
    def _reduce_default(value):
        """
        Converter:
          [a,b] -> uniformly sampled int in range (a,b)
          [a,b,c] -> one of a, b, c (.33)
          { a: 1, b: 2, c: 3 } -> one of a (.16) or b (.33) or c (.5)
        """
        if not value:
            return None
        elif isinstance(value, List) and \
                len(value) == 2 and \
                isinstance(value[0], int) and \
                isinstance(value[1], int):
            res = random.randint(value[0], value[1])
            return res
        elif isinstance(value, List):
            res = random.choice(value)
            return res
        elif isinstance(value, Dict) and all([isinstance(b, Number) for b in value.values()]):
            res = random.choices(list(value.keys()), list(value.values()))[0]
            return res
        else:
            return value

    def _template_defaults(self, templates: List[str], meta: EntityMeta):
        # find templates
        _templates_map = {}
        mro = [ cls.__name__ for cls in self.__class__.__mro__ ]
        for candidate in meta.templates_map:
            if candidate in mro:
                _templates_map = meta.templates_map[ candidate ]
                break
        res = {}
        for templ in reversed( templates ):
            if templ in _templates_map:
                res |= _templates_map[templ]
        return res

    def _template_defaults1(self, **kwargs):

        meta = kwargs.get( 'meta', EntityMeta() )  # type: EntityMeta
        res = {'meta': meta}

        # find templates
        _templates_for_cls = {}
        mro = [ cls.__name__ for cls in self.__class__.__mro__ ]
        for candidate in meta.templates_map:
            if candidate in mro:
                _templates_for_cls = meta.templates_map[ candidate ]
                break

        for field in self.__attrs_attrs__:  # type: attr.Attribute

            # if not field.init:
            #     # don't add to kwargs
            #     continue

            if field.name.startswith("_"):
                _fieldname = field.name[1:]
            else:
                _fieldname = field.name

            default = kwargs.get( _fieldname )
            # this is a little hacky, but want to allow given names in templates
            # to override randomly generated demographics
            if (default is None or "name" in field.name) and \
                    kwargs.get("templates") and _templates_for_cls:
                # Respect explicit value
                for templ_uid in reversed( kwargs.get("templates") ):
                    print( templ_uid )
                    # Overwrite in reverse priority order so earliest wins
                    templ = _templates_for_cls.get( templ_uid, {} )
                    if field.name in templ:
                        default = templ[_fieldname]

            # if not default:
            #     default = field.default
            #     if isinstance( default, attr.Factory ):
            #         if default.takes_self:
            #             # may depend on partially initialized kwargs as "self" in next step
            #             _self = {'self': types.SimpleNamespace( **res )}
            #             default = default.factory(**_self)
            #         else:
            #             default = default.factory()
            #
            # if field.metadata.get("reduce"):
            #     default = self._reduce_default( default )

            res[_fieldname] = default
        return res

    #: Local vars that can be referenced in runtime expressions and rendering
    locals: Dict = attr.ib( factory=dict )

    def ns(self, **kwargs) -> dict:
        """Get the local vars and other explicit namespace objects
        for this entity, cascades through subclasses and parent"""
        _ns = {**kwargs}
        _ns |= self.meta.ns()
        if self.parent:
            _ns |= self.parent.ns()
        _ns |= self.locals
        return _ns

    _locked: bool = attr.ib( default=False, repr=False )
    _forced: bool = attr.ib( default=False, repr=False )

    def lock(self):
        """Disable this node in the story"""
        self._locked = True

    def unlock(self, force: bool = False):
        """Enable this node in the story"""
        self._locked = False
        if force:
            self._forced = True
            self.meta.dirty = True
            if self.parent:
                self.parent.unlock( force=True )

    def avail(self, force: bool=False, **kwargs):
        """Check if this node is available, optionally force it
        to be available if it is not

        Availability _cascades_ from parents, e.g., when a scene is marked
        as locked, its child roles and blocks are locked as well.

        Flagging an entity with locals['avail'] = "ignore" will force avail
        to always return true.
        """
        if force:
            self.unlock( force=True, **kwargs )
        if self._forced:
            return True
        if self.locals.get("avail") == "ignore":
            return True
        if self.parent and not self.parent.avail( **kwargs ):
            return False
        return not self._locked

    def asdict(self) -> dict:
        """Dump entity as a dict, ignoring repr=false and un-underscoring private vars"""
        res = attr.asdict( self, filter=lambda field, val: field.repr is not False)
        res_ = {}
        for k, v in res.items():
            if k.startswith("_"):
                k = k[1:]
            res_[k] = v
        return res_

attr.resolve_types( Entity )
