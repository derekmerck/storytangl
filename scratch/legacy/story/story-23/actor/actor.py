"""
Actors are dynamic entities that can move between scenes, _mobs_ in MUD terms
"""

from typing import *
import functools

import attr

from tangl.core.entity import Entity, Renderable_
from tangl.core.entity.utils import attrs_add_reducer, reduce_defaults
from .actor_strs import ActorStrsMixin
from .actor_properties import *
from .avatar_mixin import AvatarMixin
from .decomposable import DecomposableMixin
from .outfit_detail import OutfitDetail
from .ornamentation import Ornamentation
from .demographics import Demographics

@attr.define(slots=False, hash=False, eq=False, field_transformer=attrs_add_reducer)
class Actor(ActorStrsMixin, AvatarMixin, Renderable_, Entity):

    # @attr.s
    # class Actor(IllustratedMixin,
    #             RenderableMixin,
    #             AutomorphicMixin,
    #             HasPersonalName,
    #             IsGendered,
    #             HasDialogStyles,
    #             Node):

    name: str = attr.ib(default="Jayne", metadata={"state": True})
    surname: str = attr.ib(default="Doe", metadata={"state": True})

    @property
    def full_name(self) -> str:
        return f"{self.name} {self.surname}"

    title: str = attr.ib(default=None, metadata={"state": True})

    # @property
    # def titled_full_name(self) -> str:
    #     return f"{self.name} {self.surname}"

    flavor_text: str = attr.ib( default = None, metadata={"state": True})
    origin: str = attr.ib(default=None, metadata={"state": True} )
    subtype: str = attr.ib(default=None, metadata={"state": True, "decompose": "body"})
    # This is poorly named, it's the avatar body type/race field

    age: int = attr.ib(default=None)

    # these should be mixins with handler
    avatar: dict = attr.ib(factory=dict)           #: dynamic avatar props
    stableforge: dict = attr.ib(factory=dict)      #: stableforge props

    # body
    gens: Gens = attr.ib(default=Gens.XX,
                         converter=Gens,
                         # defaults can be reduced as phenotype
                         metadata={"structure": "reduce",
                                   "decompose": "body"})

    outfit_detail: OutfitDetail = attr.ib(default=None)
    ornaments: Ornamentation = attr.ib(factory=Ornamentation, metadata={"decompose": "body"})

    # UI
    text_color: str = attr.ib(default="pink")  #: a legal web-color for the ui

    def _label(self) -> str:
        return self.full_name

    def _images(self) -> List:
        return [ f'avatar/{self.eid}' ]

    # todo: this is complicated but still not quite right, I think
    def __init__(self, *args, **kwargs):

        # Get a random demographics based on available info
        D = Demographics.instance()
        kwargs_ = {'region_id': kwargs.get("origin"),
                   "subtype": kwargs.get("subtype"),
                   "gender": str( kwargs.get("gens") ) }
        d = D.random_demographic(**kwargs_)

        if "origin" not in kwargs:
            kwargs['origin'] = d['region']

        templates = kwargs.get("templates", [])
        if d["subtype"] != "common" and d["subtype"] not in templates:
            templates.append( d['subtype'] )
            kwargs['templates'] = templates

        if "name" not in kwargs:
            kwargs["name"], kwargs["surname"] = d['name']

        # Uid needs to be reduced before super().__init__(), if there are
        # various template choices possible
        if "uid" in kwargs and not isinstance( kwargs['uid'], str ):
            kwargs['uid'] = reduce_defaults( kwargs['uid'] )

        # templates will be decomposed if possible in the regular init
        super().__init__( *args, **kwargs )

    # # alternate init
    # def __attrs_post_init__(self):
    #     try:
    #         super().__attrs_post_init__()
    #     except ValueError as e:
    #         if "full_name" in str(e) and self.desc:
    #             pass
    #     except AttributeError:
    #         pass
    #     if not self.name:
    #         from tangl.demographics import Demographics
    #         if self.is_xx:
    #             self.full_name = Demographics().name_female()
    #         else:
    #             self.full_name = Demographics().name_male()

    # # alt init2
    # # this is complicated but still not quite right, I think
    # def __init__(self, *args, _cls=None, parent: StoryNode = None, context=None,
    #              templates: list[str] = None, template_maps: dict = None,
    #              **kwargs):
    #     """
    #     Actor has its own pre-init routine that checks for pre-template demographics
    #     variables, assign defaults if necessary, and adds appropriate templates if
    #     they are missing.
    #     """
    #
    #     if context is None:
    #         context = self._mk_context()
    #
    #     if not template_maps:
    #         template_maps = self._mk_template_maps()
    #
    #     templates = templates or []
    #     templ_union = {}
    #     for key in reversed( templates ):
    #         templ = self.get_template( key, context=context, template_maps=template_maps )
    #         if templ:
    #             templ_union = templ_union | templ  # merge earliest over furthest
    #         else:
    #             print( f"Warning: Could not find template {key} for {self.__class__.__name__}")
    #     kwargs = templ_union | kwargs              # merge kwargs over templates
    #
    #     pretemplate_attribs = {'origin', 'subtype', 'gens', 'name', 'surname'}
    #
    #     # discard any that we have kwargs for
    #     for a in list( pretemplate_attribs ):
    #         if a in kwargs:
    #             pretemplate_attribs.remove( a )
    #
    #     if pretemplate_attribs:
    #         # still missing pre-template defaults
    #
    #         # Determine gens, if possible
    #         gens_field = attr.fields_dict(self.__class__)['gens']
    #         if 'gens' in kwargs:
    #             gens = kwargs['gens']
    #         else:
    #             gens = gens_field.default
    #             if isinstance(gens, attr.Factory):
    #                 if gens.takes_self:
    #                     gens = gens.factory( self )
    #                 else:
    #                     gens = gens.factory()
    #         gens = gens_field.converter( gens )
    #
    #         # Get a random demographics based on available info
    #         D = Demographics()
    #         kwargs_ = {"region_id": kwargs.get("origin"),
    #                    "subtype": kwargs.get("subtype"),
    #                    "gender": gens }
    #         d = D.random_demographic(**kwargs_)
    #
    #         if "gens" in pretemplate_attribs:
    #             pretemplate_attribs.remove("gens")
    #             kwargs["gens"] = d["gender"]
    #
    #         if "origin" in pretemplate_attribs:
    #             pretemplate_attribs.remove("origin")
    #             kwargs['origin'] = d['region']
    #
    #         if "subtype" in pretemplate_attribs:
    #             pretemplate_attribs.remove("subtype")
    #             kwargs['subtype'] = d['subtype']
    #
    #         if "name" in pretemplate_attribs:
    #             pretemplate_attribs.remove("name")
    #             kwargs["name"] = d['name'][0]
    #
    #         if "surname" in pretemplate_attribs:
    #             pretemplate_attribs.remove("surname")
    #             kwargs["surname"] = d['name'][1]
    #
    #     assert len( pretemplate_attribs ) == 0
    #
    #     # addend uncommon subtypes template
    #     if kwargs["subtype"] != "common":
    #         templates.append( kwargs['subtype'] )
    #
    #     # templates will be composed in the regular init
    #     super().__init__( *args, _cls = _cls, parent = parent, context = context,
    #                       templates = templates, template_maps = template_maps,
    #                       **kwargs )
