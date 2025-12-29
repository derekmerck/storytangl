from __future__ import annotations

import uuid

import pydantic

from tangl.media import MediaNode, HasMedia, JournalMediaItem
from tangl.media.enums import MediaRole
from tangl.graph import Node, HierarchicalStructuringHandler

# media_url **must** be available in settings
from tangl.config import settings
# assert settings.service.local.media_url

TestHasMediaNode = pydantic.create_model("TestHasMediaNode", __base__=(HasMedia, Node))

def test_media_ref_creation():

    data = {"media": [{
        'media_role': 'narrative_im',
        'url': 'http://example.com/'}]
    }

    illustrated = HierarchicalStructuringHandler.structure_node(obj_cls=TestHasMediaNode, **data)

    assert illustrated.media[0].media_role is MediaRole.NARRATIVE_IM
    assert str(illustrated.media[0].url) == data['media'][0]['url']

    print( illustrated )

    res = illustrated.media[0].get_media_resource()
    print( res )
    assert isinstance(res, JournalMediaItem)
    assert res.media_role is MediaRole.NARRATIVE_IM
    assert str(res.url) == data['media'][0]['url']


def test_image_resource():
    # todo: how do we include orientation info or other media hints?

    data = {
        'uid': uuid.uuid4(),
        'media_role': MediaRole.NARRATIVE_IM,
        # 'orientation': 'landscape',
        'url': 'http://example.com/'
        }
    res = JournalMediaItem( **data )
    print( res )
    assert res.media_role is MediaRole.NARRATIVE_IM
