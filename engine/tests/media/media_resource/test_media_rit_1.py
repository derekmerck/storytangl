from datetime import datetime

from tangl.utils.hashing import compute_data_hash
from tangl.utils.get_file_mtime import get_file_mtime
from tangl.media import MediaDataType, MediaResourceInventoryTag as MediaRIT


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


def test_resource_type_inference(temp_image_fp):
    mrt = MediaRIT(path=temp_image_fp)
    assert mrt.data_type is MediaDataType.IMAGE
