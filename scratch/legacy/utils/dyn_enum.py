"""
Create enums dynamically from source, essentially a singleton entity
without depending on the entity base class.

Requires aenum (advanced enum)
"""

import aenum
import copy
import random

class EnumHelpers(aenum.Enum, settings=aenum.MultiValue):

    def __str__(self):
        return f"{self.name.lower()}"

    def __repr__(self):
        return f"!{self.name}"

    def pick_one(self, candidates):
        if len(candidates) == 1:
            return candidates[0]
        return random.choice(candidates)

    @classmethod
    def generate_pyi(cls):
        s = f"class {cls.__name__}( aenum.Enum ):\n"
        for m in cls.__members__.values():
            s += f"    {m.name} = ...\n"
        return s

    @classmethod
    def _missing_(cls, value):
        for m in cls:
            if value.lower() == m.name.lower():
                return m
            if isinstance(m.value, tuple):
                for v in m.value:
                    if value == v:
                        return m
            if hasattr(m, '_nominal'):
                for v in m._nominal:
                    if value.lower() == v:
                        return m
        if hasattr(cls, "__aliases__"):
            for k, v in cls.__aliases__.items():
                if value in v:
                    if not isinstance(k, cls):
                        k = cls(k)
                    return k


class DynamicEnumMeta(aenum.EnumMeta):

    @classmethod
    def __prepare__(metacls, cls, bases, **kwds):
        # return a standard dictionary for the initial processing
        return {}

    def __init__(cls, *args , **kwds):
        super(DynamicEnumMeta, cls).__init__(*args)

    def __new__(metacls, cls, bases, clsdict, **kwds):
        members = []
        missing = [
               clsarg
               for clsarg in ('_fields', '_values')
               if clsarg not in clsdict
               ]
        if len(missing) > 0:
            # all three must be present or absent
            raise TypeError('missing required settings: %r' % (missing, ))

        # process
        field_spec = clsdict.pop('_fields')
        if isinstance( field_spec, (list, tuple)):
            field_spec = { k: {} for k in field_spec }
        value_spec = clsdict.pop('_values')

        clsdict["_init_"] = list( field_spec.keys() )

        for name, params in value_spec.items():
            params = copy.deepcopy( params )
            values = []
            name = name.upper()
            for field_name, field_params in field_spec.items():
                _value = None
                if isinstance(params, dict):
                    _value = params.get(field_name.strip("_"))
                elif isinstance(params, list):
                    _value = params.pop(0)
                if not _value and "default" in field_params:
                    _value = field_params['default']
                if "type" in field_params and not isinstance(_value, field_params['type']):
                    try:
                        _value = field_params['type']( _value )
                    except ValueError:
                        print( params )
                        raise
                values.append( _value )
            values = tuple(values)
            members.append(
                (name, values)
                )

        # get the real EnumDict
        enum_dict = super(DynamicEnumMeta, metacls).__prepare__(cls, bases, **kwds)
        # transfer the original dict content, _items first
        items = list(clsdict.items())
        items.sort(key=lambda p: (0 if p[0][0] == '_' else 1, p))
        for name, value in items:
            enum_dict[name] = value
        # add the members
        for name, value in members:
            enum_dict[name] = value
        return super(DynamicEnumMeta, metacls).__new__(metacls, cls, (*bases, EnumHelpers), enum_dict, settings=aenum.MultiValue, **kwds)

