"""
Up to v2.6, StoryTangl relied heavily on `attrs` for class management.  It was refactored
to Pydantic primarily for the ease of serialization/deserialization.
"""

import attr
import yaml

# abusing validator
def set_parent(self, field, value):

    if isinstance(value, list):
        for v in value:
            set_parent(self, field, v)

    elif isinstance(value, dict):
        for v in value.values():
            set_parent(self, field, v)

    elif hasattr(value, "parent"):
        value.parent = self

    return True


def cast_collection(value, cls, _cls: type = None):
    """Useful converter for lists or dicts of instances"""

    if not value:
        # maybe empty dict, empty list, None, False, 0, etc.
        return value

    if isinstance( value, cls ):

        if isinstance(value, dict) and _cls and not isinstance(list(value.keys())[0], _cls):
            # dictionary of dicts -> dict of instances
            return { k: _cls(**v) for k, v in value.items() }

        elif isinstance(value, list) and _cls and not isinstance(value[0], _cls):
            # list of dicts -> list of instances
            return [ _cls(**v) for v in value ]

        # already correct cls and subclass
        return value

    if isinstance( value, dict ):
        return cls( **value )

    if isinstance( value, str ) and cls is list:
        # list of strings
        return [ value ]

    return cls( value )


def as_dict(self) -> dict:

    def serializer( o, f, v ):
        if callable( f.repr ):
            res = f.repr( v )
            res = res.strip("'")
            return res
        elif f.repr:
            return v

    return attr.asdict( self, recurse=True, filter=lambda f, v: f.repr and v,
                        value_serializer=serializer)


def as_yaml(self) -> str:
    s = yaml.dump( self.as_dict(), sort_keys=False)
    return s
