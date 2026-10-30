"""Test cache ownership across fixture lifetimes and separate processes."""
from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import Callable
from contextlib import AbstractContextManager
from pathlib import Path

from tangl.config import settings
from tangl.utils import shelved2


def test_cache_lifetimes_are_independent(
    tmp_path: Path, isolated_shelf_cache: Path,
    cache_lifecycle: Callable[[Path], AbstractContextManager[Path]],
) -> None:
    assert shelved2.cache_dir == settings.service.paths.cache_data == isolated_shelf_cache
    assert os.environ["TANGL_SERVICE__PATHS__CACHE_DATA"] == f"@path {isolated_shelf_cache}"
    first, second = tmp_path / "first", tmp_path / "second"

    @shelved2.shelved("witness")
    def cached(value: str) -> str:
        return value

    with cache_lifecycle(first):
        cached("first")
        assert shelved2.miss_count == 1
    with cache_lifecycle(second):
        assert not second.exists()
        cached("first")
        assert (shelved2.hit_count, shelved2.miss_count) == (0, 1)


def test_overlapping_processes_clear_only_their_own_cache(tmp_path: Path) -> None:
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    sentinel = runtime / "witness"
    sentinel.write_bytes(b"developer cache sentinel")
    source = """
import sys
from tangl.utils import shelved2
@shelved2.shelved('witness')
def cached(value):
    return value
assert cached('first') == 'first'
print('ready', flush=True)
sys.stdin.readline()
shelved2.clear_shelf('witness')
assert cached('second') == 'second'
"""
    processes = []
    try:
        for number in range(2):
            env = os.environ.copy()
            env["TANGL_SERVICE__PATHS__CACHE_DATA"] = f"@path {tmp_path / f'process-{number}'}"
            processes.append(subprocess.Popen(
                [sys.executable, "-c", source], env=env, stdin=subprocess.PIPE,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            ))
        for process in processes:
            assert process.stdout.readline().strip() == "ready"
        for process in processes:
            stdout, stderr = process.communicate("continue\n", timeout=30)
            assert process.returncode == 0, (stdout, stderr)
        assert sentinel.read_bytes() == b"developer cache sentinel"
    finally:
        for process in processes:
            if process.poll() is None:
                process.kill()
                process.wait()
