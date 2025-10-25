import tempfile
from pathlib import Path

import pytest
from PIL import Image

@pytest.fixture
def temp_fp():
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp_path = Path(tmp.name)
    yield tmp_path
    tmp_path.unlink()  # Cleanup after the test


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
