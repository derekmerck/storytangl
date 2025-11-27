from pathlib import Path

from tangl.media.media_data_type import MediaDataType


def test_media_data_type_png_resolution():
    data_type = MediaDataType.from_path(Path("example.png"))

    assert data_type is MediaDataType.IMAGE
    assert data_type.ext == "png"


def test_media_data_type_members_include_other():
    assert hasattr(MediaDataType, "OTHER")
    assert MediaDataType.OTHER.ext == "bin"
