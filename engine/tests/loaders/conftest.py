from pathlib import Path

import pytest

@pytest.fixture
def media_mvp_path(resources_dir) -> Path:
    return resources_dir / "worlds" / "media_mvp"
