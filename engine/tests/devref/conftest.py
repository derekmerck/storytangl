from __future__ import annotations

from pathlib import Path

import pytest

from tangl.devref.builder import build_index


REPO_ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture(scope="session")
def devref_db_path(tmp_path_factory) -> Path:
    db_path = tmp_path_factory.mktemp("devref") / "devref.sqlite3"
    build_index(db_path=db_path, incremental=False)
    return db_path
