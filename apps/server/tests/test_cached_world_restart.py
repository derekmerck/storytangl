"""Cache-enabled multi-world isolation through a fresh JSON restore."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path


def _write_world(root: Path, label: str) -> None:
    world = root / label
    (world / "media").mkdir(parents=True)
    (world / "world.yaml").write_text(
        f"label: {label}\ndomain_module: {label}_domain\nscripts: story.yaml\nmedia_dir: media\n"
    )
    (world / "media" / "picture.svg").write_text(f"<svg><!-- {label} --></svg>")
    (world / "story.yaml").write_text(f"""\
label: {label}
metadata:
  start_at: intro.start
scenes:
  intro:
    blocks:
      start:
        content: {label} start
        media:
          - name: picture.svg
            media_role: narrative_im
        actions:
          - text: Continue
            successor: middle
      middle:
        content: {label} middle
        effects:
          - "graph.locals['marker'] = '{label}'"
        actions:
          - text: Finish
            successor: end
      end:
        content: {label} end
""")
    (world / f"{label}_domain.py").write_text(f'''\
from tangl.core import BehaviorRegistry
from tangl.presentation.projection import InfoAffordance, KvListValue, ProjectedSection
from tangl.presentation.values import KvRow

world_dispatch = BehaviorRegistry(label="{label}.projection")
CATALOG = {{"witness": "{label}"}}

def advertise(**_kw):
    return InfoAffordance(channel_id="ui-mystery", label="World witness")

def project(*, ctx, request, **_kw):
    if "ui-mystery" not in request.requested_channels():
        return None
    return ProjectedSection(section_id="world_state", title="World witness", kind="mystery",
        value=KvListValue(items=[KvRow(key="catalog_key", value=CATALOG["witness"]),
                                 KvRow(key="marker", value=ctx.graph.locals.get("marker", "none")),
                                 KvRow(key="namespace_marker",
                                       value=ctx.get_ns().get("marker", "none"))]))

world_dispatch.register(advertise, task="advertise_story_info_channels")
world_dispatch.register(project, task="get_story_info")

def get_authorities():
    return [world_dispatch]
''')


def test_two_worlds_and_users_survive_cold_json_restart(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[3]
    worlds = tmp_path / "worlds"
    for label in ("isolation_alpha", "isolation_beta"):
        _write_world(worlds, label)
    shutil.copytree(repo / "engine/tests/resources/anthology_worlds/shelf", worlds / "shelf")
    for key in ("user_data", "story_media", "cache_data"):
        (tmp_path / key).mkdir()
    env = {
        **os.environ,
        "PYTHONPATH": os.pathsep.join(map(str, (repo / "engine/src", repo / "apps/server/src"))),
        "TANGL_SERVICE__PATHS__CACHE_DATA": f"@path {tmp_path / 'cache_data'}",
        "TANGL_SERVICE__CACHES__SHELVED": "true",
    }
    script = Path(__file__).parent / "helpers_server/cached_world_restart.py"
    for phase in ("seed", "restore"):
        result = subprocess.run([sys.executable, str(script), phase, str(tmp_path)],
                                cwd=repo, env=env, capture_output=True, text=True, timeout=90)
        assert result.returncode == 0, f"{phase}:\n{result.stdout}\n{result.stderr}"
        assert "Exception ignored" not in result.stderr
        assert "sqlite3." not in result.stderr and "dbm.error" not in result.stderr
