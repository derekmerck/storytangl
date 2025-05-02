from __future__ import annotations
from typing import Iterable, TYPE_CHECKING, Optional, ClassVar

from pydantic import Field

from tangl.core.entity.handlers import NamespaceHandler # Templated
from tangl.core.graph.handlers import Associating, AssociationHandler
from tangl.story import StoryNode
from .gender import Gender
# from tangl.media import HasMedia
# from tangl.lang.has_personal_name import HasPersonalName
# from tangl.lang.gens import Gens
# from .look import Look
# from .vocals import Vocals
# from .outfit import HasOutfit

if TYPE_CHECKING:
    from .role import Role
else:
    Role = StoryNode

class Actor(Associating, StoryNode):

    gender: Gender = Gender.XX  # default to female


    name_: str = Field(None, alias="name")

    @property
    def name(self):
        return self.name_

    @NamespaceHandler.strategy()
    def _add_demographics(self):
        return {
            'name': self.name
        }

    # actors may come with titles and assets, particularly wearables or adv equipment
    # assets: dict[ClassName, list[AssetScript] | dict[UniqueLabel, AssetScript]] = None

    # #todo: support multiple looks?  Or is this default look and scene-role can override?
    # @property
    # def look(self) -> Look:
    #     return self.find_child(Look)
    #
    # @property
    # def vocals(self) -> Vocals:
    #     return self.find_child(Vocals)
    #
    # voice: Optional[dict] = None

    # @property
    # def demographic(self) -> Demographic:
    #     return self.find_child(Demographic)
    #
    # # convenience
    #
    # @property
    # def outfit(self) -> Outfit:
    #     return self.look.outfit
    #
    # @property
    # def gens(self):
    #     return self.demographic.gens

    # @property
    # def is_xx(self) -> bool:
    #     return self.gens.is_xx
    #
    # @property
    # def age(self):
    #     return self.demographic.age
    #
    # # Implements HasAvatar
    # def get_avatar(self):
    #     AvatarHandler = object
    #     return AvatarHandler.get_avatar(self)

    # todo: namespace should be modified by the _current role_ if there
    #   are multiple roles, not just the parent role.  That is, ns should
    #   include the _current scene_ being evaluated.  We have no mechanism
    #   to track that currently.

    # todo: should be able to inherit outfit and title from assigned role


    # these should be mixins with handler
    # avatar: dict = attr.ib(factory=dict)           #: dynamic avatar props
    # stableforge: dict = attr.ib(factory=dict)      #: stableforge props

    # ui_color: str = None

    # Implements HasDialogProps

    # def get_dialog_style(self, dialog_class = None):
    #     if self.ui_color:
    #         return {"font-color": self.ui_color}
    #
    # def get_dialog_image(self, dialog_class = None):
    #     # for actor, dialog_class will be attitude: neutral, happy, sad, wink, etc.
    #     if x := list(self.media):
    #         # todo: this is mocked
    #         return x[0]

    # def get_dialog_images(self, *modifiers: str) -> dict[str, dict]:
    #     # mb_role is something like "waif.happy"
    #     ims_by_role = { im.media_role: im for im in self.images }
    #     media_ref = None
    #     for modifier in modifiers:
    #         try:
    #             role = ImageRole( f"dialog_{modifier}" )
    #             if role in ims_by_role:
    #                 media_ref = ims_by_role[ImageRole.DIALOG]
    #         except ValueError:
    #             pass
    #     if ImageRole.DIALOG in ims_by_role:
    #         media_ref = ims_by_role[ImageRole.DIALOG]
    #     if media_ref:
    #         im = media_ref.find_media()
    #         role = im.pop('media_role')
    #         return {role: im }
    #
    # @classmethod
    # def register_actor_look_filters(cls, env: jinja2.Environment):
    #     """
    #     she is {{ actor | height }} -> she is tall | short | etc
    #     her hair is {{ actor | hair_color }} -> her hair is blonde | brunette | etc
    #
    #     - age (apparent age)
    #     - gender (apparent gender)
    #     - height
    #     - body-type
    #     - skin-tone
    #     - hair-style, hair-len, hair-color
    #     - outfit desc
    #
    #     see Pronoun.register_jinja_filters
    #     """
    #     ...

