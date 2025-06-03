import tempfile
from datetime import datetime
from pathlib import Path

import pytest
from PIL import Image

from tangl.utils.compute_data_hash import compute_data_hash
from tangl.utils.get_file_mtime import get_file_mtime
from tangl.media.media_resource import MediaDataType, MediaResourceInventoryTag as MediaRIT

@pytest.fixture
def temp_fp():
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp_path = Path(tmp.name)
    yield tmp_path
    tmp_path.unlink()  # Cleanup after the test

def test_compute_file_hash(temp_fp):
    # Mock the file content
    file_content = b"test data"
    temp_fp.write_bytes(file_content)

    file_hash = compute_data_hash(temp_fp)
    expected_hash = compute_data_hash(file_content)
    assert file_hash == expected_hash

def test_get_mtime(temp_fp):
    current_time = datetime.now()
    temp_fp.touch()  # Update the file's mtime to the current time

    mtime = get_file_mtime(temp_fp)
    assert mtime.replace(microsecond=0) == current_time.replace(microsecond=0)


def test_file_rit_initialization(temp_fp):
    resource_tag = MediaRIT(path=temp_fp, label='test', data_type=MediaDataType.IMAGE)
    assert resource_tag.label == "test"
    assert resource_tag.data_type == MediaDataType.IMAGE


@pytest.fixture
def temp_image_fp():
    # solid red test image
    width, height = 100, 100
    image = Image.new('RGB', (width, height), color=(255, 0, 0))

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        tmp_path = Path(tmp.name)
        image.save(tmp_path)

    yield tmp_path
    tmp_path.unlink()  # Cleanup after the test


def test_resource_type_inference(temp_image_fp):
    mrt = MediaRIT(path=temp_image_fp)
    assert mrt.data_type is MediaDataType.IMAGE
