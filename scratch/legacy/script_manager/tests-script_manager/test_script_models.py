
import pytest
from pydantic import ValidationError

from tangl.media import MediaItemScript


def test_media_ref_exactly_1():
    # Example with exactly one field provided
    valid_media = MediaItemScript(url='http://example.com/image.png')
    print(valid_media)

    with pytest.raises(ValidationError):
        # Example with more than one field provided, which will raise a validation error
        invalid_media = MediaItemScript(url='http://example.com/image.png', data='base64image==')
        print( invalid_media )

    with pytest.raises(ValidationError):
        # Example with no fields provided, which will also raise a validation error
        invalid_media = MediaItemScript()
        print( invalid_media )
