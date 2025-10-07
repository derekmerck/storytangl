from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("sphinx")
from sphinx.cmd.build import build_main


DOCS_SOURCE = Path(__file__).resolve().parents[3] / "docs" / "source"


def test_sphinx_docs_build_html(tmp_path, monkeypatch) -> None:
    """Ensure the Sphinx configuration stays buildable."""
    monkeypatch.setenv("STORYTANGL_OFFLINE", "1")
    output_dir = tmp_path / "html"
    result = build_main(
        [
            "-b",
            "html",
            "-W",
            "--keep-going",
            "-n",
            str(DOCS_SOURCE),
            str(output_dir),
        ]
    )
    assert result == 0, "sphinx-build should exit cleanly"
    assert any(output_dir.iterdir()), "the html builder should emit files"
