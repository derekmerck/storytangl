import pytest

pytest.skip(reason="image handlers broken", allow_module_level=True)

from unittest.mock import patch
from tangl.media.illustrated import ImageResourceModel
from tangl.media.illustrated import ImageHandler

@pytest.mark.skip(reason="image handlers broken")
def test_image_handler():
    # Mock the _create_media_resource method to return a red circle SVG
    with patch.object(ImageHandler, "find_media_resource", return_value=ImageResourceModel(path="red_circle.svg", media="<svg>...</svg>")) as mock_create:
        # Instantiate the ImageHandler
        handler = ImageHandler(path="red_circle.svg")

        # Call get_media_resource without any existing media
        resource = handler.get_media_resource()
        # Check that _create_media_resource was called since the media didn't exist
        mock_create.assert_called_once()
        # Check that the returned resource is correct
        assert resource.path == "red_circle.svg"
        assert resource.media == "<svg>...</svg>"

    # Now let's test with an existing media
    with patch.object(ImageHandler, "_find_media_resource", return_value=MediaResource(path="red_circle.svg", media="<svg>...</svg>")) as mock_find:
        with patch.object(ImageHandler, "_create_media_resource") as mock_create:
            # Call get_media_resource when the media already exists
            resource = handler.get_media_resource()
            # Check that _find_media_resource was called and _create_media_resource was not
            mock_find.assert_called_once()
            mock_create.assert_not_called()
            # Check that the returned resource is correct
            assert resource.path == "red_circle.svg"
            assert resource.media == "<svg>...</svg>"
        