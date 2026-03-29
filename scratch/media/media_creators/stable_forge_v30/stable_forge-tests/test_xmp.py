import uuid

from unittest.mock import Mock
from tangl.media.illustrated.stableforge.xmp_handler import XmpDataModel
from tangl.info import __author__, __author_email__

def test_spec2xmp():
    # Create a mock StableForgeSpec object
    kwargs = {
        'prompt': 'mock_prompt',
        'n_prompt': 'mock_neg_prompt',
        'guid': uuid.uuid4(),
        'model': 'mock_model',
        'digest': 'mock_digest',
        'actors': ['mock_actor1', 'mock_actor2'],
        'nsfw': True
    }

    # Call the method under test
    xmp_tags = XmpDataModel(**kwargs).xmp_tags

    # Assert that the returned dictionary contains the expected values
    assert xmp_tags['Xmp.tiff.Software'] == 'StableDiffusion'
    assert xmp_tags['Xmp.dc.creator'] == __author__
    assert xmp_tags['Xmp.Iptc4xmpCore.CreatorContactInfo/Iptc4xmpCore:CiEmailWork'] == __author_email__
    # assert xmp_tags['Xmp.photoshop.TransmissionReference'] == 'mock_uid'
    assert xmp_tags['Xmp.dc.description'] == 'mock_prompt NOT mock_neg_prompt'
    assert xmp_tags['Xmp.tiff.Model'] == 'mock_model'
    # assert xmp_tags['Xmp.photoshop.Instructions'] == str({'mock_key': 'mock_value'})
    # assert xmp_tags['Xmp.iptcExt.DigImageGUID'] == 'mock_digest'
    assert set(xmp_tags['Xmp.dc.subject']) == {'actor|mock_actor1', 'actor|mock_actor2', 'nsfw'}
    assert xmp_tags['Xmp.iptcExt.PersonInImage'] == ['mock_actor1', 'mock_actor2']
    assert xmp_tags['Xmp.GettyImagesGIFT.Personality'] == 'mock_actor1;mock_actor2'
