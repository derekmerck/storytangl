
from __future__ import annotations

import random
import types
from typing import *
import inspect
from numbers import Number

import attr

from .meta import EntityMeta
from .utils import mk_eid, as_uid


@attr.define(init=False, slots=False)
class Entity:

    # Automorphic handlers

    __subclass_map__: ClassVar[dict] = dict()  #: registered subclass overrides
    def __init_subclass__(cls, **kwargs):
        cls.__subclass_map__[ cls.__name__ ] = cls

    def __new__(cls, *args, **kwargs):
        # try to identify any relevant override classes
        init_cls = cls
        for k, v in kwargs.items():
            if k.endswith("_cls"):
                init_cls = cls.__subclass_map__[ v ]
        if 'meta' in kwargs:
            meta = kwargs['meta']
            override_cls = meta.override_cls( init_cls )
            if override_cls:
                init_cls = override_cls
        return super().__new__(init_cls)

    def __init__(self, *args, **kwargs):
        """Automorphism"""
        if "meta" not in kwargs:
            meta_cls = attr.fields_dict( self.__class__ )["meta"].default.factory
            kwargs['meta'] = meta_cls()
        if "template_maps" in kwargs:
            kwargs['meta']._template_maps = kwargs['template_maps']
        kwargs = self._set_defaults_from_templates( kwargs )
        kwargs = self._set_defaults_from_attrs( kwargs )
        kwargs = self._reduce_defaults( kwargs )
        kwargs = self._structure_child_entities( kwargs )
        kwargs = self._discard_unused_kwargs( kwargs )
        self.__attrs_init__(**kwargs)

    def _set_defaults_from_templates(self, kwargs) -> dict:
        templates = kwargs.get('templates')
        meta = kwargs.get('meta')
        template_maps = meta.template_maps( self.__class__ )
        if templates and template_maps:
            defaults = {}
            for templ in reversed( templates ):
                defaults |= template_maps.get( templ, {} )
            kwargs = defaults | kwargs
        return kwargs

    def _set_defaults_from_attrs(self, kwargs) -> dict:
        for f in attr.fields(self.__class__):
            if not f.init:
                continue
            field_name = f.name.lstrip("_")
            if field_name not in kwargs:
                default = f.default
                if isinstance( default, attr.Factory ):
                    if default.takes_self:
                        _kwargs = {'self': types.SimpleNamespace( **kwargs )}
                    else:
                        _kwargs = {}
                    default = default.factory(**_kwargs)
                kwargs[ field_name ] = default
        return kwargs

    def _reduce_defaults(self, kwargs) -> dict:
        for f in attr.fields(self.__class__):
            if f.metadata.get("reduce"):
                field_name = f.name.lstrip("_")
                value = kwargs[field_name]
                value = self._reduce_default( value )
                kwargs[field_name] = value
        return kwargs

    def _reduce_default(self, value):
        if isinstance( value, list ) and len( value ) == 2 and isinstance(value[0], int) and isinstance(value[1], int):
            return random.randint(value[0], value[1])
        elif isinstance( value, list ) and len( value ) > 1:
            return random.choice( value )
        elif isinstance( value, dict ) and all( [isinstance(v, Number) for v in value.values() ]):
            choices = list( value.keys() )
            weights = list( value.values() )
            return random.choices(choices, weights=weights)[0]
        return value

    def _discard_unused_kwargs(self, kwargs) -> dict:
        field_names = [ f.name.lstrip("_") for f in attr.fields( self.__class__ ) ]
        for k in list( kwargs.keys() ):
            if k not in field_names:
                del( kwargs[ k ] )
        return kwargs

    def _structure_child_entities(self, kwargs):

        try:
            attr.resolve_types(self.__class__)
        except TypeError as e:
            print( f"Failed to resolve types for {self.__class__}" )
            pass
        meta = kwargs['meta']

        def structure_child(child_cls, data, **kwargs):
            if isinstance( data, child_cls ):
                return data
            if isinstance(data, str):
                # update child_kwargs if there is a "consumes_str" flag on a field
                for field in attr.fields(child_cls):
                    if "consumes_str" in field.metadata:
                        data = {field.name.lstrip("_"): data}
            if not isinstance( data, dict ):
                print( data )
                raise TypeError
            return child_cls(**data, **kwargs, parent=self, meta=meta)

        def structure_child_list(child_cls, kwargs_list: list[dict], field_name: str = "unknown"):
            res = []
            for i, v in enumerate( kwargs_list ):
                if isinstance(v, dict) and 'uid' not in v:
                    v['uid'] = f"{field_name[:2]}{i}"
                res.append(structure_child(child_cls, v))
            return res

        def structure_child_dict(child_cls, kwargs_dict: dict[str, dict], key_class):
            res = {}
            for k, v in kwargs_dict.items():
                if isinstance(v, dict) and 'uid' not in v:
                    v['uid'] = k
                try:
                    # best effort to cast to the key class, but won't work if
                    # it's something generic like "Enum"
                    kk = key_class(k)
                except ValueError:
                    kk = k
                res[kk] = structure_child(child_cls, v)
            return res

        for f in attr.fields( self.__class__ ):
            if not f.init:
                continue
            field_name = f.name.lstrip("_")
            value = kwargs[field_name]
            if value:
                if isinstance(value, Entity):
                    continue
                elif inspect.isclass(f.type) and issubclass(f.type, Entity):
                    child_cls = f.type
                    value = structure_child( child_cls, value )
                    kwargs[field_name] = value
                elif hasattr( f.type, "__origin__" ) and (f.type.__origin__ is list ) and \
                        hasattr(f.type, "__args__") and len( f.type.__args__) > 0 and \
                        issubclass(f.type.__args__[0], Entity):
                    child_cls = f.type.__args__[0]
                    value = structure_child_list( child_cls, value, field_name=field_name )
                    kwargs[field_name] = value
                elif hasattr( f.type, "__origin__" ) and (f.type.__origin__ is dict ) and \
                        hasattr(f.type, "__args__") and len( f.type.__args__) > 1 and \
                        issubclass(f.type.__args__[1], Entity):
                    key_cls = f.type.__args__[0]
                    child_cls = f.type.__args__[1]
                    value = structure_child_dict( child_cls, value, key_cls )
                    kwargs[field_name] = value
        return kwargs

