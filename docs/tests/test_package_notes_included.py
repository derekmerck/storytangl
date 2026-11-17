"""Every design note beside the engine code is included in the API reference."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "engine" / "src" / "tangl"
API = ROOT / "docs" / "src" / "api"


def test_every_package_note_has_an_api_page() -> None:
    missing = []
    for note in sorted(PACKAGE.rglob("*.md")):
        rel = note.relative_to(PACKAGE)
        page = API / rel
        source = note.relative_to(ROOT).as_posix()
        if not page.exists() or "{include} " not in page.read_text() or source not in page.read_text():
            missing.append(f"{source} -> {page.relative_to(ROOT).as_posix()}")
    assert not missing, "package notes without an including API page:\n" + "\n".join(missing)
