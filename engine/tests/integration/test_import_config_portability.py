"""Import and packaged-path portability contracts."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import textwrap


REPO_ROOT = Path(__file__).resolve().parents[3]


def _tree(root: Path) -> set[Path]:
    return {path.relative_to(root) for path in root.rglob("*")}


def test_imports_are_side_effect_free_without_dicebear(tmp_path: Path) -> None:
    cwd = tmp_path / "cwd"
    home = tmp_path / "home"
    xdg_cache = tmp_path / "xdg-cache"
    for path in (cwd, home, xdg_cache):
        path.mkdir()
    before = _tree(tmp_path)

    source = textwrap.dedent(
        """
        import importlib.abc
        import importlib.util
        from pathlib import Path
        import sys

        class BlockDiceBear(importlib.abc.MetaPathFinder):
            def find_spec(self, fullname, path=None, target=None):
                if fullname == "dicebear" or fullname.startswith("dicebear."):
                    raise AssertionError(f"unexpected DiceBear import: {fullname}")
                return None

        sys.meta_path.insert(0, BlockDiceBear())

        import tangl

        script_path = Path(sys.argv[1])
        spec = importlib.util.spec_from_file_location("comfy_batch_import_witness", script_path)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)

        assert not any(
            name == "dicebear" or name.startswith("dicebear.") for name in sys.modules
        )

        from tangl.config import settings

        root = Path.cwd()
        expected = {
            "client_dist": root / "apps/web/dist",
            "docs": root / "docs/build/html",
            "user_data": root / "tmp/user",
            "story_media": root / "tmp/media",
            "cache_data": root / "tmp/cache",
        }
        actual = {
            name: Path(getattr(settings.service.paths, name)) for name in expected
        }
        assert actual == expected
        assert all(root in path.parents for path in actual.values())
        assert not any(path.exists() for path in actual.values())
        """
    )
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("TANGL_")
    }
    python_path = [str(REPO_ROOT / "engine/src"), str(REPO_ROOT)]
    if env.get("PYTHONPATH"):
        python_path.append(env["PYTHONPATH"])
    env.update(
        {
            "HOME": str(home),
            "XDG_CACHE_HOME": str(xdg_cache),
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONPATH": os.pathsep.join(python_path),
        }
    )

    subprocess.run(
        [sys.executable, "-c", source, str(REPO_ROOT / "scripts/comfy_batch.py")],
        cwd=cwd,
        env=env,
        check=True,
    )

    assert _tree(tmp_path) == before
