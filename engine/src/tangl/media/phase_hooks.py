from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

from tangl.core import Priority, Selector
from tangl.vm.dispatch import on_provision

from .media_data_type import MediaDataType
from .media_resource.media_provisioning import _story_media_manager, _write_story_media
from .media_resource.media_resource_inv_tag import (
    MediaRITStatus,
    MediaResourceInventoryTag as MediaRIT,
)
from .worker_dispatcher import WorkerResult
from .media_creators.media_spec import MediaSpec
from tangl.utils.hashing import hashing_func


def _ctx_meta(ctx: Any) -> dict[str, Any]:
    meta = getattr(ctx, "meta", None)
    if isinstance(meta, dict):
        return meta
    return {}


def _run_once(ctx: Any, key: str) -> bool:
    meta = _ctx_meta(ctx)
    phase_state = meta.setdefault("_media_phase_state", set())
    if key in phase_state:
        return False
    phase_state.add(key)
    return True


def _get_worker_dispatcher(ctx: Any) -> Any | None:
    meta = _ctx_meta(ctx)
    dispatcher = meta.get("worker_dispatcher")
    if dispatcher is not None:
        return dispatcher
    getter = getattr(ctx, "get_meta", None)
    if callable(getter):
        return getter().get("worker_dispatcher")
    return None


def _iter_story_rits(graph: Any) -> Iterable[MediaRIT]:
    if graph is None:
        return ()
    return graph.find_all(Selector(has_kind=MediaRIT))


def _hash_execution_spec(payload: dict[str, Any] | None) -> str | None:
    if not isinstance(payload, dict) or not payload:
        return None
    return hashing_func({"data": payload}).hex()


def _infer_result_data_type(rit: MediaRIT, result: WorkerResult) -> MediaDataType | None:
    if isinstance(result.data_type, MediaDataType):
        return result.data_type
    if rit.data_type is not None:
        return rit.data_type
    if result.path is not None:
        return MediaDataType.from_path(result.path)
    if isinstance(result.data, str) and result.data.lstrip().startswith("<svg"):
        return MediaDataType.VECTOR
    if isinstance(result.data, (bytes, bytearray)):
        return MediaDataType.OTHER
    return None


def _resolve_story_label(rit: MediaRIT) -> str:
    if isinstance(getattr(rit, "label", None), str) and rit.label:
        return rit.label
    adapted = getattr(rit, "adapted_spec", None)
    if isinstance(adapted, dict):
        label = adapted.get("label")
        if isinstance(label, str) and label.strip():
            return label
    return "media"


def _register_worker_path(result_path: Path, *, ctx: Any) -> Path:
    manager = _story_media_manager(_ctx=ctx)
    if manager is None:
        return result_path
    try:
        result_path.resolve().relative_to(manager.resource_path.resolve())
    except (OSError, ValueError):
        return result_path
    if result_path.exists():
        manager.register_file(result_path)
    return result_path


def _apply_worker_result(rit: MediaRIT, result: WorkerResult, *, ctx: Any) -> None:
    if not result.success:
        rit.status = MediaRITStatus.FAILED
        rit.job_id = None
        return

    data_type = _infer_result_data_type(rit, result)
    if data_type is not None:
        rit.data_type = data_type

    if result.path is not None:
        rit.path = _register_worker_path(Path(result.path), ctx=ctx)
        rit.data = None
    elif result.data is not None:
        manager = _story_media_manager(_ctx=ctx)
        if manager is not None and data_type is not None:
            fingerprint = getattr(rit, "adapted_spec_hash", None) or getattr(rit, "job_id", None) or "media"
            output_path = _write_story_media(
                result.data,
                manager=manager,
                base_name=_resolve_story_label(rit),
                fingerprint=str(fingerprint),
                data_type=data_type,
            )
            rit.path = output_path
            rit.data = None
        else:
            rit.data = result.data
            rit.path = None
    else:
        rit.status = MediaRITStatus.FAILED
        rit.job_id = None
        return

    execution_spec = result.execution_spec
    if execution_spec is None:
        adapted_spec = getattr(rit, "adapted_spec", None)
        execution_spec = dict(adapted_spec) if isinstance(adapted_spec, dict) else None
    rit.execution_spec = execution_spec
    rit.execution_spec_hash = _hash_execution_spec(execution_spec)
    rit.worker_id = result.worker_id
    rit.generated_at = result.generated_at or datetime.now()
    rit.status = MediaRITStatus.RESOLVED
    rit.job_id = None


@on_provision(priority=Priority.EARLY)
def reconcile_media_jobs(caller: Any, *, ctx: Any, **_: Any) -> None:
    """Poll async worker jobs once per planning pass and update story RITs."""
    _ = caller
    if not _run_once(ctx, "reconcile_media_jobs"):
        return

    dispatcher = _get_worker_dispatcher(ctx)
    if dispatcher is None:
        return

    graph = getattr(ctx, "graph", None)
    for rit in _iter_story_rits(graph):
        if getattr(rit, "status", MediaRITStatus.RESOLVED) != MediaRITStatus.RUNNING:
            continue
        job_id = getattr(rit, "job_id", None)
        if not isinstance(job_id, str) or not job_id:
            continue
        result = dispatcher.poll(job_id)
        if result is None:
            continue
        _apply_worker_result(rit, result, ctx=ctx)


@on_provision(priority=Priority.LATE)
def dispatch_media_jobs(caller: Any, *, ctx: Any, **_: Any) -> None:
    """Submit newly-accepted pending RITs once per planning pass."""
    _ = caller
    if not _run_once(ctx, "dispatch_media_jobs"):
        return

    dispatcher = _get_worker_dispatcher(ctx)
    if dispatcher is None:
        return

    graph = getattr(ctx, "graph", None)
    for rit in _iter_story_rits(graph):
        if getattr(rit, "status", MediaRITStatus.RESOLVED) != MediaRITStatus.PENDING:
            continue
        if getattr(rit, "job_id", None):
            continue
        adapted_spec = getattr(rit, "adapted_spec", None)
        if not isinstance(adapted_spec, dict) or not adapted_spec:
            continue
        rit.job_id = dispatcher.submit(dict(adapted_spec))
        rit.status = MediaRITStatus.RUNNING
