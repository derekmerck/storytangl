import random
import functools
from typing import *
import uuid
import base64
import numbers

import attr

from .protocols import Uid, Entity


# def new_eid() -> Eid:
#     val = uuid.uuid4().bytes
#     encoded = base64.b64encode(val, b"Aa")
#     str = encoded.decode("utf8")
#     return str[0:8]

def as_eid( value ) -> Uid:

    if isinstance(value, dict):
        for k, v in value.items():
            value[k] = v.eid
    elif isinstance(value, list):
        for i, v in enumerate(value):
            value[i] = v.eid
    elif hasattr(value, "eid"):
        value = value.eid

    try:
        return str( value )
    except AttributeError as e:
        print( e )
        print( object.__repr__( value ) )
        print( value.__dict__ )
        raise


T = TypeVar("T")

def normalize_list_arg( obj: Union[list[T], T]) -> List[T]:
    if not isinstance( obj, list ):
        return [obj]
    return obj


# # If you have children, you need a factory
# def structure_children( self: Entity, field, value: T ) -> T:
#     if hasattr( self, "factory" ) and self.factory:
#         factory = self.factory  # type=EntityFactory
#     else:
#         factory = None
#
#     if isinstance(value, dict):
#         entity_cls = field.type.__args__[1]
#         entity_typ = entity_cls.__name__
#         for k, v in value.items():
#             v = v or {}
#             if "uid" not in v:
#                 v['uid'] = k
#             elif len( v['uid'] ) == 1:
#                 v['uid'] = [k, v['uid']]
#             else:
#                 v['uid'].insert( k, 0 )
#
#             if factory:
#                 el = factory.new_entity( entity_typ, **v, parent=self, ctx=self.ctx )
#             else:
#                 el = entity_cls( **v, parent=self, ctx=self.ctx )
#             value[k] = el
#         return True
#
#     elif isinstance(value, list):
#         entity_cls = field.type.__args__[0]
#         entity_typ = entity_cls.__name__
#         prefix = field.name[0:2]
#         for i, v in enumerate( value ):
#             if "uid" not in v:
#                 _uid = f"{prefix}{i}"  # i.e., "ro0" for role[0]
#                 v['uid'] = _uid
#             if factory:
#                 el = factory.new_entity( entity_typ, **v, parent=self, ctx=self.ctx )
#             else:
#                 el = entity_cls( **v, parent=self, ctx=self.ctx )
#             value[i] = el
#         return True


def reduce_defaults(v):
    """This transformation converts a subtype default range into a single
    value as the class is generated.  Use as an attrs converter."""

    if isinstance(v, list):
        if len(v) == 2 and isinstance(v[0], int) and isinstance(v[1], int):
            return random.randint(v[0], v[1])
        else:
            return random.choice(v)

    elif isinstance(v, dict) and \
            all([isinstance(vv, numbers.Number) for vv in v.values()]):
        choices = list(v.keys())
        weights = list(v.values())

        return random.choices(choices, weights=weights)[0]

    else:
        return v


def attrs_add_reducer(cls: type, fields: List[attr.Attribute]) -> List[attr.Attribute]:
    """Attach reduce_defaults to any field with {structure: reduce} in meta.
    Use as an attrs class field_transformer.
    """
    res = []
    for field in fields:
        if field.metadata.get("structure") == "reduce":
            f = field.type
            def conv(f, v):
                if v:
                    v = reduce_defaults(v)
                return f(v)
            res.append( field.evolve(converter=functools.partial(conv, f) ) )
        else:
            res.append( field )
    return res

# def references(obj: 'Entity'):
#     state = obj.__dict__
#     for field in attr.fields(obj.__class__):
#         if field.metadata.get("reduce") == "reference":
#             value = state[ field.name ]
#             if isinstance(value, dict):
#                 for k, v in value.items():
#                     value[k] = v.eid
#             elif isinstance(value, list):
#                 for i, v in enumerate( value ):
#                     value[i] = v.eid
#             elif hasattr(value, "eid"):
#                 state[ field.name ] = value.eid
#
#     return state
#
#
# def dereference(obj: 'Entity'):
#
#     ctx = obj.ctx
#
#     for field in attr.fields(obj.__class__):
#         if field.metadata.get("reduce") == "reference":
#             value = getattr( obj, field.name )
#             if isinstance(value, dict):
#                 for k, v in value.items():
#                     value[k] = ctx[ v ]
#             elif isinstance(value, list):
#                 for i, v in enumerate( value ):
#                     value[i] = ctx[ v ]
#             elif isinstance(value, str):
#                 setattr( obj, field.name, ctx[ value ] )

