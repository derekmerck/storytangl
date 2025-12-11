from __future__ import annotations
import base64
import functools
import uuid
import random
from enum import Enum
from numbers import Number
from typing import *
from functools import partial
from collections import UserDict

import attr


class NodeContext(UserDict):
    """
    Structured metadata, templates and subclass maps for a related collection
    of nodes, and an instance map that can lookup nodes by pid or uid/path
    """

    def __init__(self, cls_template_maps: dict = None, class_map = None,
                 *args, **kwargs):
        self._cls_template_maps: dict[str, dict] = cls_template_maps or {}
        self._class_map: dict[str, type[Node]] = class_map or {}
        super().__init__( *args, **kwargs )

    def add_templates(self, cls_: type[Node] | str, **kwargs):
        if not isinstance(cls_, str) and issubclass(cls_, Node):
            cls_ = cls_.__name__
        if cls_ not in self._cls_template_maps:
            self._cls_template_maps[cls_] = {}
        self._cls_template_maps[cls_] |= kwargs

    def get_template(self, cls_: type[Node] | str, key: str) -> dict:
        if not isinstance(cls_, str) and issubclass(cls_, Node):
            cls_ = cls_.__name__
        return self._cls_template_maps.get(cls_, {}).get(key)

    def get_class(self, cls_: type[Node] | str) -> type[Node]:
        if not isinstance(cls_, str) and issubclass(cls_, Node):
            cls_ = cls_.__name__
        return self._class_map.get(cls_)

    @functools.cached_property
    def _by_path(self) -> dict:
        res = {}
        for k, v in self.data.items():
            try:
                res[v.path] = v
            except (TypeError, AttributeError) as e:  # pragma: no cover
                print("Failed to render a path")
                print( e )
                print( v )
                raise
        return res

    def __setitem__(self, key, value):
        super().__setitem__( key, value )
        if hasattr( self, "_by_path" ):
            delattr(self, '_by_path' )

    def add(self, item):
        if not hasattr( item, "pid"):  # pragma: no cover
            raise TypeError(f"Cannot contextualize {item}")
        self[item.pid] = item

    def __contains__(self, item):
        if item in self.data or item in self._by_path:
            return True

    def __getitem__(self, item):
        if item in self.data:
            return self.data[item]
        elif item in self._by_path:
            return self._by_path[item]
        raise KeyError

    # def get(self, key: str, default = None) -> AutoMorph:
    #     if key in self:
    #         return self[key]
    #     else:
    #         return default

    def filter(self, f: Callable) -> list:
        res = []
        for v in self.data.values():
            if f(v):
                res.append( v )
        return res


def new_pid() -> str:
    """Random private unique ID"""
    uid = uuid.uuid4()
    data = uid.bytes
    msg = base64.b64encode( data, altchars=b'Az' )
    res = msg.decode('utf8')[:12]
    return res


def repr_as_pid(value: list | dict | Node ) -> list | dict | Node | None:
    """Represent item as its pid (for references to avoid recursion)"""

    if not value:
        return
    elif isinstance( value, list ):
        res = [ x.pid for x in value ]
    elif isinstance( value, dict ):
        res = { k: x.pid for k, x in value.items() }
    elif hasattr( value, "pid"):
        res = value.pid
    else:  # pragma: no cover
        raise TypeError
    return res


def repr_as_str(value: list | dict | Node ) -> list | dict | Node | None:
    """Represent item as its consumable string"""

    if not value:
        return
    elif isinstance( value, list ):
        res = [ x.expr for x in value ]
    elif isinstance( value, dict ):
        res = { k: x.expr for k, x in value.items() }
    elif hasattr( value, "pid"):
        res = value.expr
    else:  # pragma: no cover
        raise TypeError
    return res

@attr.define( init=False, slots=False )
class Node:



    parent: Node = attr.ib( default=None, repr=False, eq=False )
    @property
    def root(self):
        root = self
        while root.parent:
            root = root.parent
        return root

    @property
    def path(self):
        """Handle to index a node by uid-path in a context, such as `scene/ro1` or `scene/my_block`"""
        res = str(self.uid)
        root = self
        while root.parent and hasattr(root.parent, 'uid'):
            res = str( root.parent.uid ) + "/" + res
            root = root.parent
        return res

    #: Metadata and index for a collection of nodes
    context: NodeContext = attr.ib(factory=NodeContext, repr=False, eq=False)

    def _mk_context(self) -> NodeContext | None:
        from tangl.utils.singleton import Singletons
        if isinstance(self, Singletons):
            return
        field = attr.fields_dict(self.__class__)['context']
        if field.default.takes_self:
            context = field.default.factory(self)
        else:
            context = field.default.factory()
        return context

    def _mk_template_maps(self) -> dict | None:
        from tangl.utils.singleton import Singletons
        if isinstance(self, Singletons):
            template_maps = self.__class__._as_templates()
            return template_maps

    def __attrs_post_init__(self):
        try:
            super().__attrs_post_init__()  # Singletons init
        except AttributeError:
            pass
        if self.context is not None:
            self.context.add(self)

    def __init_node__(self, **kwargs):
        pass

    def as_dict(self, discard=None) -> dict:
        """Dump entity as a dict, ignoring repr=false and un-underscoring private vars"""

        discard = discard or []

        def serialize(inst, field, value):
            try:
                return field.repr( value )
            except:
                pass

            if isinstance( value, Enum):
                return value.value

            return value

        def include( field, val ) -> bool:
            if isinstance( field.default, attr.Factory ):
                if field.default.takes_self:
                    default = field.default.factory(self)
                else:
                    default = field.default.factory()
            else:
                default = field.default
            if (field.repr is False) or \
                    (not val and not default) or \
                    (val == default) or \
                    field.name in discard:
                return False
            return True

        res = attr.asdict( self,
                           recurse=True,
                           filter=include,
                           value_serializer=serialize)

        def fix_keys( value: dict ):
            res_ = {}
            for k, v in value.items():
                if isinstance(k, Enum):
                    k = k.value
                if isinstance(k, str) and k.startswith("_"):
                    k = k[1:]
                if isinstance(v, dict):
                    v = fix_keys( v )
                res_[k] = v
            return res_

        res = fix_keys( res )
        return res


def reduce_default(value, conv: Callable = None):
    if isinstance( value, list ) and len( value ) == 2 and isinstance(value[0], int) and isinstance(value[1], int):
        value = random.randint(value[0], value[1])
    elif isinstance( value, list ) and len( value ) > 1:
        value = random.choice( value )
    elif isinstance( value, dict ) and all( [isinstance(v, Number) for v in value.values() ]):
        choices = list( value.keys() )
        weights = list( value.values() )
        value = random.choices(choices, weights=weights)[0]

    if conv is not None:
        return conv( value )
    return value

def attrs_reduce_transform(cls, fields: list[attr.Attribute,...] ) -> list:
    res = []
    for f in fields:
        if f.metadata.get("reduce") and f.converter is not reduce_default:
            converter = functools.partial( reduce_default, conv=f.converter )
            g = f.evolve( converter=converter )
            res.append( g )
        else:
            res.append( f )
    return res

@attr.define( init=False, slots=False, field_transformer=attrs_reduce_transform )
class AutoMorph( Node ):
    """
    AutoMorphic Nodes can self-shape into any derived class
    and lookup sets of standard arguments from templates.

    A '_cls' override argument will cast itself to that class if
    possible.

    A 'templates' list argument will look for class templates
    and merge them into the given kwargs.

    It also structures any of its attributes that are AutoMorphic
    children and uses the "reduce" flag in metadata to add a default
    reduction converter.
    """

    def __new__(cls, *args, _cls: type[Node] | str = None, context: NodeContext = None, **kwargs):
        """Class automorphism"""
        if not _cls:
            for k, v in kwargs.items():
                if k.endswith('_cls'):
                    _cls = v
        _cls = cls.get_class( _cls, context=context )
        cls = _cls or cls
        return object.__new__(cls)

    def __init__(self, *args, _cls=None, parent: Node = None, context=None,
                 templates: list[str] = None, template_maps: dict = None,
                 **kwargs):
        """Templating and pre-structuring automorphism"""

        for k in list(kwargs.keys()):
            if k.endswith("_cls"):
                kwargs.pop(k)

        if context is None:
            context = self._mk_context()

        if not template_maps:
            template_maps = self._mk_template_maps()

        templates = templates or []
        templ_union = {}
        for key in reversed( templates ):
            templ = self.get_template( key, template_maps=template_maps, context=context )
            if templ:
                templ_union = templ_union | templ  # merge earliest over furthest
            else:
                print( f"Warning: Could not find template {key} for {self.__class__.__name__}")
        kwargs = templ_union | kwargs              # merge kwargs over templates

        kwargs = self.structure_children( **kwargs, parent=self, context=context, template_maps=template_maps )

        self.__attrs_init__( *args, **kwargs, parent=parent, context=context )

    _class_map: ClassVar[dict] = dict()

    @classmethod
    def __init_subclass__(cls, **kwargs):
        cls._class_map[cls.__name__] = cls

    @classmethod
    def get_class(cls, cls_: type[Node] | str, context: NodeContext = None):
        cls_ = cls_ or cls
        if isinstance(cls_, type) and issubclass( cls_, Node ):
            cls_ = cls_.__name__
        if context is not None:
            res = context.get_class( cls_ )
            if res:
                return res
        return cls._class_map.get( cls_ )

    _template_map: ClassVar[dict] = dict()

    @classmethod
    def add_template(cls, key: str, value: dict):
        cls._template_map[key] = value

    @classmethod
    def get_template(cls, key: str, template_maps: dict = None, context: NodeContext = None):
        if template_maps and key in template_maps:
            return template_maps[key]
        if context is not None:
            templ = context.get_template( cls, key)
            if templ:
                return templ
        return cls._template_map.get( key )

    @classmethod
    def structure_children(cls, parent: AutoMorph = None, context: NodeContext = None,
                           template_maps: dict = None, **kwargs):

        def structure_child(cls, data: dict | str | bool | AutoMorph, uid=None ) -> AutoMorph | None:
            if data is None:
                return None
            if isinstance( data, cls ):
                return data
            if isinstance(data, str):
                # update child_kwargs if there is a "consumes_str" flag on a field
                for field in attr.fields(cls):
                    if "consumes_str" in field.metadata:
                        data = {field.name.lstrip("_"): data}
            return cls(**data, uid=uid, parent=parent, context=context, template_maps=template_maps)

        def structure_list(cls, value: list[dict], auto_uid="child{i:02d}") -> list[AutoMorph]:
            res = []
            for i, v in enumerate(value):
                if isinstance(v, dict) and 'uid' in v:
                    uid = v.pop('uid')
                else:
                    uid = auto_uid.format(i=i, v=v)
                res.append( structure_child( cls, v, uid=uid ) )
            return res

        def structure_dict(cls, value: dict[str, dict], auto_uid="{k}") -> dict[str, AutoMorph]:
            res = {}
            for k, v in value.items():
                if isinstance(v, dict) and 'uid' in v:
                    uid = v.pop('uid')
                else:
                    uid = auto_uid.format(k=k, v=v)
                res[k] = structure_child( cls, v, uid=uid )
            return res

        try:
            attr.resolve_types(cls)
        except TypeError as e:
            print( f"Failed to resolve types for {cls}" )
            pass
        fields = attr.fields_dict( cls )
        res = {}

        for k, v in kwargs.items():

            if "_" + k in fields:
                f = fields["_" + k]
            elif k in fields:
                f = fields[k]
            else:
                res[k] = v
                continue

            converter = None

            if hasattr( f.type, "__origin__") and hasattr( f.type, "__args__"):
                try:
                    if f.type.__origin__ is dict and issubclass( f.type.__args__[1], AutoMorph ):
                        converter = partial( structure_dict, f.type.__args__[1] )
                    elif f.type.__origin__ is list and issubclass( f.type.__args__[0], AutoMorph ):
                        auto_uid = f.metadata.get('auto_uid', f.name[0:2]+"{i}")
                        converter = partial( structure_list, f.type.__args__[0], auto_uid=auto_uid )
                except TypeError:
                    pass
            elif isinstance( f.type, type ):
                if issubclass( f.type, AutoMorph ):
                    converter = partial( structure_child, f.type )

            if converter:
                res[k] = converter( v )
            else:
                res[k] = v

        return res

    @staticmethod
    def define(cls):
        res = attr.define( cls, slots=False, init=False, field_transformer=attrs_reduce_transform )
        return res
