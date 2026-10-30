"""Shelf operations own their handles and serialize threads by file path."""
from __future__ import annotations

import dbm
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier, Event

import pytest

from tangl.utils import shelved2


@pytest.fixture(autouse=True)
def enable_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(shelved2, "SHELVED_CACHE_ENABLED", True)


def test_threads_reuse_invalidate_unshelf_and_clear() -> None:
    calls = []

    @shelved2.shelved("shared")
    def value(key: str) -> int:
        calls.append(key)
        return len(calls)

    with ThreadPoolExecutor(max_workers=1) as worker:
        assert value("main", check_value=1) == 1
        assert worker.submit(value, "main", check_value=1).result(timeout=5) == 1
        assert worker.submit(value, "worker", check_value=1).result(timeout=5) == 2
        assert value("worker", check_value=1) == 2
        assert worker.submit(value, "main", check_value=2).result(timeout=5) == 3
        worker.submit(shelved2.unshelf, "shared", "main").result(timeout=5)
        assert value("main", check_value=2) == 4
        path, lock = shelved2._path_and_lock("shared")
        worker.submit(shelved2.clear_shelf, "shared").result(timeout=5)
        assert shelved2._path_and_lock("shared")[1] is lock
        assert value("worker", check_value=1) == 5
        assert path.parent.exists()


def test_simultaneous_cold_access_computes_once() -> None:
    gate = Barrier(3)
    entered, release = Event(), Event()
    calls = []

    @shelved2.shelved("cold")
    def value(key: str) -> str:
        calls.append(key)
        entered.set()
        assert release.wait(5)
        return key

    def run() -> str:
        gate.wait(timeout=5)
        return value("one")

    with ThreadPoolExecutor(max_workers=2) as workers:
        futures = [workers.submit(run) for _ in range(2)]
        gate.wait(timeout=5)
        try:
            assert entered.wait(5)
        finally:
            release.set()
        assert [future.result(timeout=5) for future in futures] == ["one", "one"]
    assert calls == ["one"]
    assert (shelved2.hit_count, shelved2.miss_count) == (1, 1)


def test_failed_computation_releases_shelf_for_other_thread() -> None:
    @shelved2.shelved("failure")
    def value(key: str) -> str:
        if key == "bad":
            raise RuntimeError("witness")
        return key

    with ThreadPoolExecutor(max_workers=1) as worker:
        with pytest.raises(RuntimeError, match="witness"):
            worker.submit(value, "bad").result(timeout=5)
        assert value("good") == "good"
        assert worker.submit(value, "good").result(timeout=5) == "good"


def test_absent_clear_and_unshelf_do_not_create_cache() -> None:
    shelved2.clear_shelf("absent")
    shelved2.unshelf("absent", "key")
    assert not shelved2.cache_dir.exists()


def test_disabled_and_declined_miss_do_not_compute(monkeypatch: pytest.MonkeyPatch) -> None:
    @shelved2.shelved("declined", skip_if_not_cached=True)
    def declined() -> None:
        raise AssertionError("must not compute")

    with pytest.raises(shelved2.CacheMissError):
        declined()
    monkeypatch.setattr(shelved2, "SHELVED_CACHE_ENABLED", False)
    with pytest.raises(shelved2.CacheMissError):
        declined()

    @shelved2.shelved("disabled")
    def direct() -> str:
        return "computed"

    assert direct() == "computed"


def test_backend_error_does_not_delete_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    shelved2.cache_dir.mkdir()
    marker = shelved2.cache_dir / "fault"
    marker.write_bytes(b"preserve")
    def fail(*args, **kwargs):
        raise dbm.error[0]("locked or damaged")
    monkeypatch.setattr(shelved2.shelve, "open", fail)
    with pytest.raises(dbm.error):
        shelved2.shelved("fault")(lambda: None)()
    with pytest.raises(dbm.error):
        shelved2.unshelf("fault", "key")
    with pytest.raises(dbm.error):
        shelved2.clear_shelf("fault")
    assert marker.read_bytes() == b"preserve"


def test_worker_shelf_has_no_exit_cleanup_error(tmp_path: Path) -> None:
    source = """
from concurrent.futures import ThreadPoolExecutor
from tangl.utils.shelved2 import shelved
@shelved('worker')
def cached(x): return x
with ThreadPoolExecutor(max_workers=1) as pool:
    assert pool.submit(cached, 'ok').result(timeout=5) == 'ok'
"""
    env = {**os.environ, "TANGL_SERVICE__PATHS__CACHE_DATA": f"@path {tmp_path / 'child'}"}
    result = subprocess.run([sys.executable, "-c", source], env=env, text=True,
                            capture_output=True, timeout=20)
    assert result.returncode == 0, result.stderr
    assert not result.stderr
