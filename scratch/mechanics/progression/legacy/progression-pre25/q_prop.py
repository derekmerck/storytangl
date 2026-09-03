"""
Quality properties are bookkeepers for dynamic badges that can improve or
decay over time.

They can be attached to classes declaratively, or through a class specification that
programmatically injects them to an existing class's attrs fields using a field transform.
This is useful for specifying properties and badges together in a kind of domain
specific language.
"""

from __future__ import annotations
from typing import *
import functools

import attr

from tangl.utils.cast_collection import wrap_cast_to as cast_to
from tangl.story.asset.badge import Badge
from .quality import Quality

@attr.define(init=False)
class QualityProperty:

    intrinsics: dict[Quality] = None
    currencies: dict[Quality] = None
    skills: dict[Quality] = None

    def __init__(self, *args, badges: dict[dict] = None, skills: dict[dict], **kwargs):

        for k, v in badges.items() or {}:
            Badge(uid=k, **v)

        for k, v in skills.items() or {}:
            if "minor_effects" in v:
                Badge(uid=f'{k}_minor', effects=v['minor_effects'], conditions=[f'{k} very low'])
                del v['minor_effects']
            if "effects" in v:
                Badge(uid=k, effects=v['effects'], conditions=[f'{k} ok'], hides=[f'{k}_minor'])
                del v['effects']
            if "major_effects" in v:
                Badge(uid=f'{k}_major', effects=v['major_effects'],
                      conditions=[f'{k} very good'], hides=[f'{k}_minor', k])
                del v['major_effects']

        self.__attrs_init__(*args, skills=skills, **kwargs)


def wrap_inject_props( props: dict[dict] ) -> Callable:

    def inject_props(cls, fields, props=props):
        res = [*fields]
        for k, v in props.items():

            subprops = v.get('intrinsics').keys() + v.get('skills').keys() + v.get('currencies').keys()

            attrib = attr.Attribute(name=k,
                                    default=None,
                                    validator=None,
                                    repr=True,
                                    cmp=True,
                                    hash=None,
                                    init=True,
                                    inherited=False,
                                    type=QualityProperty,
                                    metadata={'subprops': subprops},
                                    converter=cast_to( dict[QualityProperty] ))
            res.append(attrib)

            # attach accessors to the base class
            for p in subprops:
                def getx(k, p, self):
                    prop = getattr(self, k)
                    res = getattr(prop, p)
                    return res

                def setx(k, p, self, val):
                    prop = getattr(self, k)
                    setattr(prop, p, val)
                    return res

                subprop_delegate = property(
                    functools.partial(getx, k, p),
                    functools.partial(setx, k, p)
                )
                setattr(cls, p, subprop_delegate)
        return res

    return functools.partial( inject_props, props=props )


def make_qprops_stub(cls):
    res = f"class {cls.__name__}:\n"
    fields = attr.fields(cls)
    for field in fields:
        if field.type is QualityProperty:
            for p in field.metadata['subprops']:
                res += f"  {p}: Quality\n"


class PropertyManager:

    properties: dict[QualityProperty]

    def __getattr__(self, item):
        if item in self.properties:
            return self.properties[item]
        return super().__getattr__(item)
        # raises AttributeError if not found
