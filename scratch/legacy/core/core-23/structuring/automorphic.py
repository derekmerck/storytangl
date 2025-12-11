"""
Feature desiderata:

- nodes can self-cast to subclasses through their _class_map variable
- nodes can type cast their own attributes and children during initialization
- nodes with a template manager can look up their attributes and children's defaults during initialization
- story nodes may be "structured" from kwarg templates by a manager (the world) at story instantiation
- or story nodes may be generated dynamically by another node (like an Actor by a Role) as needed
- generic story nodes should not require a world association but use one opportunistically
- story templates are generally written/stored as yaml with a near 1-to-1 relationship between document dicts and object kwargs.
- we need to be able to dump and load a full story state of heavily interlinked and nested nodes for persistence.  Right now that's done with pickle, which is fine and very gracefully handles links, but has drawbacks wrt scalability.
- we want to be able to dump and load states by unstructuring and structuring nodes from/to kwargs, including enough info to recover custom class types and handling deeply nested node structures.
- yaml, json, and bson should all be valid targets for inflation/deflation
"""

from __future__ import annotations
import random
import io
from typing import ClassVar, Type
from pathlib import Path
from typing import get_type_hints, get_args, Any
from numbers import Number

import attr
import yaml

from tangl.utils.attrs_ext import as_dict as attrs_as_dict
from tangl.core.node import Node


class SelfCastingMixin:
    """
    Automorphic subclasses can be factoried from any superclass by including a
    'node_cls' param in the call to "from_dict".

    Uses the 'index' param if it exists to check for override classes.
    """

    # _class_map: ClassVar = {'Node': Node}

    @classmethod
    def register_subclass(cls):
        cls._class_map[cls.__name__] = cls

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls.register_subclass()

    @classmethod
    def get_cls(cls, data: str | dict ) -> Type[AutomorphicMixin]:

        # By default, just return the class
        _cls = cls

        node_cls = None
        # Look for a suggested class
        if isinstance(data, dict) and 'node_cls' in data:
            node_cls = data['node_cls']
        elif isinstance(data, str):
            node_cls = data

        if node_cls:
            try:
                _cls = cls._class_map[node_cls]
            except KeyError:
                raise KeyError(f"Unknown node_cls lookup request key {node_cls} (Not in {list(cls._class_map.keys())}")

        # Check in the index for a world-specific class override for this type
        if isinstance(data, dict) and 'index' in data:
            try:
                _cls = data['index'].pm.hook.on_new_node(cls=_cls)[0]
            except (KeyError, AttributeError):
                # No index or index doesn't have a plugin manager
                pass

        return _cls

    def as_dict(self):
        # todo: this doesn't work b/c concise_as_dict() doesn't recurse properly
        #       using _this_ as_dict for Automorphs to include node_cls, maybe
        #       need to include an extra fields lambda?
        # Need to addend the 'node_cls' for deserialization if it's not
        # a base class type, like Block is the base class for ChallengeBlock
        # etc.  We will just always include it as part of the repr.

        def add_node_cls(inst: SelfCastingMixin, value: dict):
            if isinstance(inst, SelfCastingMixin):
                value['node_cls'] = type( self.__class__.__name__)

        res = attrs_as_dict( self, unstructuring_callbacks=[ add_node_cls ] )

        return res

    to_dict = as_dict      # alias
    unstructure = as_dict  # alias


class SelfTypingMixin:
    """
    Automorphs can manage their children in variously named fields, which
    serve as casting type-hints.

    For example, the "blocks" parameter in a Scene template should be created
    as objects of type Block and added to the parent's children attribute.

    This mixin attempts to infer the field name and type from class introspection
    given the new node's parameters.
    """

    @classmethod
    def from_kwargs(cls, data: dict):

        # deal with recognized kwargs for attrs-friendly fields
        attribute_names = set(attrib.name.lstrip("_") for attrib in attr.fields(cls))
        recognized_data = {key: value for key, value in data.items() if key in attribute_names}

        # create the object
        try:
            node = cls(**recognized_data)
        except TypeError:
            print(f"Failed on {recognized_data}")
            raise

        # look at the fields and cast any automorphic objects down
        # to the proper type.  This obviates the need for a converter and
        # secondary pass to add the parent relationship.
        for attrib in attr.fields(cls):
            try:
                if issubclass(attrib.type, AutomorphicMixin):
                    val_ = getattr(node, attrib.name)
                    val_['parent'] = node
                    val = attrib.type.from_dict(val_)
                    setattr( node, attrib.name, val )
            except TypeError:
                pass

        # deal with unrecognized kwargs and misnamed children
        unrecognized_data = {key: value for key, value in data.items() if key not in attribute_names}
        for key, value in unrecognized_data.items():
            if hasattr(cls, key):
                # This is a legit target field, for example, in Scene, we have
                # the property `def blocks() -> dict[Block]:...`, so we should
                # cast a field named "blocks" to class Block and add them as children.
                attrib = getattr(cls, key)
                if isinstance(attrib, property) and isinstance(value, list | dict):
                    # It might be a child type, try to infer the class
                    type_hints = get_type_hints(attrib.fget)
                    return_hint = type_hints['return']
                    child_cls = get_args(return_hint)[-1]  # list[node] or dict[str, Node]
                    try:
                        if isinstance(value, list):
                            # it's a list of children
                            for child_data in value:
                                child_data['parent'] = node
                                child = child_cls.from_dict(child_data)
                                node.add_child(child)
                        elif isinstance(value, dict):
                            # it's a dict of children, flatten it into a list
                            for uid, child_data in value.items():
                                child_data['parent'] = node
                                child_data['uid'] = uid
                                child = child_cls.from_dict(child_data)
                                node.add_child(child)
                    except (KeyError, AttributeError, TypeError) as e:
                        # it's improperly annotated for children, so complain
                        print( 'Self typing exception on', e )
                        raise TypeError(f"Tried to cast children to improperly annotated property {key} in {cls.__name__} (val={value}, uid={data.get('uid')})")
            elif key not in ["node_cls", "parent"]:
                raise TypeError(f"No such field {key} in {cls.__name__} (val={value}, uid={data.get('uid')})")

        return node

class SelfTemplatingMixin:
    """
    Automorphic subclasses can refer to template dictionaries in a manager
    by including a 'template_ids' param in the call to "from_dict".

    Values from corresponding template dicts will be merged with the node
    kwargs as default values when a value doesn't already exist.

    This process is conceptually similar to a software config that can take
    defaults for different environments from a variety of different mechanisms.

    SelfTemplating also includes a "reduce" function that can be called on
    fields that sample from a distribution to finalize their value.

    If reducing a field should result in different template assignments, it
    is  recommended to handle the first phase reductions of these key attributes
    as a class-specific pre-process, probably in `attrs.__pre_init__`.

    For example, an NPC may have an attribute `background=[baker,soldier]`.
    After sampling, we add either 'baker' or 'soldier' to the `template_ids`
    field and now might have conditionally distinct ranges to sample from for
    `strength` and `cooking` attributes.

    Following the config metaphor above, this is similar to sampling the
    environment type before building your environment-specific config and
    sampling individual values.
    """

    @classmethod
    def get_kwargs(cls, data: dict):
        # todo: This loop should probably be in the template manager?
        while 'template_ids' in data:  # in case templates refer to other templates!
            try:
                defaults = data['index'].get_templates( data['template_ids'] )
                data = defaults | data
            except (KeyError, AttributeError):
                pass
        return data

    @classmethod
    def sample_dist(cls, value):
        if isinstance( value, list ) and len(value) == 2 and \
                all( [isinstance(v, int) for v in value] ):
            # It's an int range
            return random.randint( value[0], value[1] )
        elif isinstance(value, list) and len(value) > 1:
            # It's a pick-one
            return random.choice(value)
        elif isinstance( value, dict ) and \
                all( [isinstance(v, Number) for v in value.values() ]):
            # It's a weighted dist { a: 3, b: 1 }
            choices = list(value.keys())
            weights = list(value.values())
            return random.choices(choices, weights=weights, k=1)[0]

        return value

    @classmethod
    def reduce(cls, node: AutomorphicMixin):
        for field in attr.fields( cls ):
            field: attr.Attribute
            if field.metadata.get('reduce'):
                val = getattr( node, field.name )
                res = cls.sample_dist( val )
                setattr( node, field.name, res )


class AutomorphicMixin(SelfTemplatingMixin, SelfTypingMixin, SelfCastingMixin):
    """
    Automorphic - Self-Shaping

    Mixin class supporting the creation of heterogeneously-typed nodes from structured
    data like YAML.

    `from_data` is a class factory method that invokes several self-shaping systems.

    1. Self-casting to subclasses with 'node_cls' param
    2. Self-typing for misnamed attributes (specifically children keyed for type casting)
    3. Self-templating if a template manager is available with 'template_ids' param

    Following the `cattrs` paradigm, creating properly typed nodes from flat dictionaries
    is called "structuring" in the package and the converse, reducing a node to a flat
    dictionary is called "unstructuring".

    This helps distinguish this process from other kinds of serialization/deserialization
    such as pickling.
    """

    @classmethod
    def from_dict(cls, data: dict):
        _data = cls.get_kwargs(data)
        _cls = cls.get_cls(data)
        node = _cls.from_kwargs(_data)
        _cls.reduce(node)
        return node

    structure = from_dict

    # No need for a special 'as_dict' func for serialization, b/c we don't
    # need to unsample random distributions or convert children back to
    # field-name type-hints.

    # These are convenience functions.
    # If using a persistence backend, it will convert to and from kwarg dicts
    # automatically.

    @classmethod
    def from_yaml(cls, data: Path | str):
        if isinstance(data, Path):
            with open(data) as f:
                res = yaml.safe_load(f)
        else:
            res = yaml.safe_load(data)

        if not isinstance(res, dict):
            raise TypeError("Method assumes loading root of single node tree")

        return cls.from_dict(res)

    def as_yaml(self, f: io.StringIO = None) -> Any:
        data = self.as_dict()
        yaml.safe_dump(data, f)

    to_yaml = as_yaml
