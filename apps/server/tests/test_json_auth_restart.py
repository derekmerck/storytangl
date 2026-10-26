"""JSON auth recovery is independent of unavailable ledger World authorities."""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys


def test_json_auth_startup_and_profile_in_a_fresh_process(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[3]
    shutil.copytree(repo / "worlds/reference", tmp_path / "worlds/reference")
    for key in ("user_data", "story_media", "cache_data"):
        (tmp_path / key).mkdir()
    script = Path(__file__).parent / "helpers_server/json_auth_restart.py"
    sources = [repo / "engine/src", repo / "apps/server/src"]
    env = {**os.environ, "PYTHONPATH": os.pathsep.join(map(str, sources))}
    for phase in ("seed", "restore"):
        result = subprocess.run(
            [sys.executable, str(script), phase, str(tmp_path)],
            cwd=repo, env=env, capture_output=True, text=True, timeout=45,
        )
        assert result.returncode == 0, f"{phase}:\n{result.stdout}\n{result.stderr}"
