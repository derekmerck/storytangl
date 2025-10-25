from typing import ClassVar

from tangl.core.handler import on_render_content
# from tangl.story.story import StoryNode
from tangl.media import MediaResourceInventoryTag as MediaRIT

from .credential import Credential

class IdCard(Credential):
    """
    This is a special credential type that includes a holder description
    (height, weight, age, hair color, etc.) and an optional photo
    """

    @property
    def label(self):
        return f'id_card:{self.parent.name}'

    @property
    def id_card_photo(self) -> MediaRIT:
        return self.find_child(MediaRIT)

    @property
    def id_card_number(self):
        return Credential.guid2credential(self.guid)

    @on_render_content.register()
    def _provide_id_card_info(self, **kwargs) -> dict:
        return {
            'holder_name': self.parent.full_name,
            # 'holder_id': self.id_card_number,
            'holder_text': self.id_card_text,
            'holder_photo': self.id_card_photo
        }
