#!/usr/bin/env python3
"""Submit templated ComfyUI jobs without story provisioning. See comfy_batch.md."""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import sys
import tempfile
import time
from pathlib import Path
from typing import Literal

import requests
from jinja2 import StrictUndefined, TemplateError
from jinja2.sandbox import SandboxedEnvironment
from pydantic import BaseModel, ConfigDict, Field, JsonValue

from tangl.media.media_creators.comfy_forge._common import configured_comfy_url, history_error
from tangl.media.media_creators.comfy_forge.comfy_api import ComfyApi

Workflow = dict[str, dict[str, JsonValue]]
REPO_ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = SandboxedEnvironment(undefined=StrictUndefined, autoescape=False)


class JobInput(BaseModel):
    """CLI/manifest value object, not graph-owned state."""

    model_config = ConfigDict(extra="forbid")
    params: dict[str, JsonValue] = Field(default_factory=dict)
    images: dict[str, Path] = Field(default_factory=dict)


class BatchInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    workflow: Path
    params: dict[str, JsonValue] = Field(default_factory=dict)
    jobs: list[JobInput] = Field(min_length=1)


class Source(BaseModel):
    path: Path
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    upload_name: str


class JobReceipt(BaseModel):
    request_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    params: dict[str, JsonValue]
    sources: dict[str, Source]
    workflow: Workflow
    submitted_workflow: Workflow | None = None
    prompt_id: str | None = None
    status: Literal[
        "prepared",
        "submitting",
        "submission_unknown",
        "rejected",
        "submitted",
        "completed",
        "failed",
    ] = "prepared"
    submitted_at: float | None = None
    history: dict[str, JsonValue] | None = None
    downloads: list[dict[str, str]] = Field(default_factory=list)
    error: str | None = None


class BatchReceipt(BaseModel):
    """Versioned JSON transport receipt; no RITs, registries, or runtime pointers."""

    version: Literal[1] = 1
    endpoint: str
    template: str
    jobs: list[JobReceipt]


def fingerprint(value: JsonValue) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def render_workflow(
    template: str, params: dict[str, JsonValue], images: dict[str, str]
) -> Workflow:
    """Render trusted workflow structure; use ``tojson`` for supplied string values."""
    if "images" in params:
        raise ValueError("'images' is reserved for the source-image bindings")
    try:
        rendered = TEMPLATES.from_string(template).render(**params, images=images)
    except TypeError as exc:
        # Jinja's tojson raises TypeError rather than UndefinedError for a missing value.
        raise ValueError(f"Undefined or non-JSON workflow template value: {exc}") from exc
    workflow = json.loads(rendered)
    if (
        not isinstance(workflow, dict)
        or not workflow
        or any(
            not isinstance(node, dict)
            or not isinstance(node.get("class_type"), str)
            or not isinstance(node.get("inputs"), dict)
            for node in workflow.values()
        )
    ):
        raise ValueError("Expected ComfyUI API-format node JSON, not the UI workflow export")
    return workflow


def prepare_jobs(template: str, jobs: list[JobInput], endpoint: str) -> BatchReceipt:
    """Validate all inputs offline and collapse identical concrete requests."""
    prepared: dict[str, JobReceipt] = {}
    for job in jobs:
        sources = {}
        for slot, path in job.images.items():
            path = path.resolve()
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            sources[slot] = Source(
                path=path, sha256=digest, upload_name=f"sha256-{digest}{path.suffix.lower()}"
            )
        workflow = render_workflow(
            template, job.params, {slot: source.upload_name for slot, source in sources.items()}
        )
        digest = fingerprint({
            "workflow": workflow,
            "sources": {slot: source.sha256 for slot, source in sources.items()},
        })
        prepared.setdefault(
            digest,
            JobReceipt(
                request_sha256=digest, params=job.params, sources=sources, workflow=workflow,
            ),
        )
    if not prepared:
        raise ValueError("At least one job is required")
    return BatchReceipt(endpoint=endpoint, template=template, jobs=list(prepared.values()))


def save_receipt(path: Path, receipt: BatchReceipt) -> None:
    """Replace a complete receipt atomically; one process owns a receipt file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, delete=False
    ) as f:
        temp = Path(f.name)
        f.write(receipt.model_dump_json(indent=2) + "\n")
    temp.replace(path)


def resume_receipt(path: Path, prepared: BatchReceipt) -> BatchReceipt:
    if not path.exists():
        save_receipt(path, prepared)
        return prepared
    saved = BatchReceipt.model_validate_json(path.read_text())
    if saved.endpoint != prepared.endpoint or [j.request_sha256 for j in saved.jobs] != [
        j.request_sha256 for j in prepared.jobs
    ]:
        raise ValueError("Receipt belongs to a different endpoint or batch; use a new receipt path")
    # A source may have been renamed since an offline preparation run.
    for old, new in zip(saved.jobs, prepared.jobs):
        if old.status == "prepared":
            old.sources = new.sources
            old.params = new.params
    saved.template = prepared.template
    save_receipt(path, saved)
    return saved


def submit_jobs(api: ComfyApi, receipt: BatchReceipt, path: Path) -> None:
    """Upload inputs and submit each new job once; never retry an ambiguous POST."""
    if receipt.endpoint != api.endpoint():
        raise ValueError("Receipt endpoint does not match the worker")
    uncertain = [
        j.request_sha256 for j in receipt.jobs
        if j.status in {"submitting", "submission_unknown"}
    ]
    if uncertain:
        raise ValueError(f"Reconcile uncertain submissions before resuming: {uncertain}")
    uploads: dict[str, str] = {}
    for job in receipt.jobs:
        if job.status != "prepared":
            continue
        images = {}
        for slot, source in job.sources.items():
            data = source.path.read_bytes()
            if hashlib.sha256(data).hexdigest() != source.sha256:
                raise ValueError(f"Source changed since preparation: {source.path}")
            if source.upload_name not in uploads:
                uploads[source.upload_name] = api.upload_image(data, filename=source.upload_name)
            images[slot] = uploads[source.upload_name]
        job.submitted_workflow = render_workflow(receipt.template, job.params, images)
        job.status = "submitting"
        save_receipt(path, receipt)
        try:
            job.prompt_id = api.queue_prompt(job.submitted_workflow)
        except (requests.RequestException, ValueError) as exc:
            job.status = "submission_unknown"
            if isinstance(exc, requests.HTTPError) and exc.response is not None:
                if exc.response.status_code in {400, 422}:
                    job.status = "rejected"
                job.error = f"{exc}: {exc.response.text}"
            else:
                job.error = str(exc)
            save_receipt(path, receipt)
            raise
        job.status = "submitted"
        job.submitted_at = time.time()
        save_receipt(path, receipt)
        print(f"Submitted {job.prompt_id} ({job.request_sha256[:12]})", file=sys.stderr)


def download_outputs(api: ComfyApi, job: JobReceipt, output_dir: Path) -> None:
    """Keep exact output bytes (including embedded PNG metadata), plus SHA-256."""
    if output_dir.resolve().is_relative_to(REPO_ROOT):
        raise ValueError("Download media outside the repository (PNG/JPG Git LFS safety)")
    destination = output_dir / job.request_sha256
    destination.mkdir(parents=True, exist_ok=True)
    downloads = []
    for index, ref in enumerate(api.extract_output_image_refs(job.history)):
        filename = Path(ref["filename"]).name
        target = destination / f"{index:03d}-{filename}"
        data = api.fetch_image_bytes(
            ref["filename"], subfolder=ref["subfolder"], folder_type=ref["type"]
        )
        if target.exists() and target.read_bytes() != data:
            raise ValueError(f"Refusing to overwrite a different artifact: {target}")
        target.write_bytes(data)
        downloads.append({
            **ref, "path": str(target.resolve()), "sha256": hashlib.sha256(data).hexdigest(),
        })
    job.downloads = downloads


def collect_jobs(
    api: ComfyApi,
    receipt: BatchReceipt,
    path: Path,
    *,
    wait: bool = False,
    timeout: float = 3600,
    poll_interval: float = 2,
    output_dir: Path | None = None,
) -> bool:
    """Poll all submitted jobs; timeout only stops this waiter, not remote execution."""
    if timeout <= 0 or not 0 < poll_interval <= 60:
        raise ValueError("Timeout must be positive and poll interval must be in (0, 60]")
    if receipt.endpoint != api.endpoint():
        raise ValueError("Receipt endpoint does not match the worker")
    deadline = time.monotonic() + timeout
    downloaded: set[str] = set()
    while True:
        for job in receipt.jobs:
            if job.status == "submitted":
                if job.prompt_id is None:
                    raise ValueError("Submitted receipt is missing prompt_id")
                history = api.get_history(job.prompt_id)
                if history is not None:
                    job.history = history
                    error = history_error(history)
                    status = history.get("status")
                    if error:
                        job.status, job.error = "failed", error
                    elif isinstance(status, dict) and status.get("completed") is True:
                        job.status = "completed"
                    save_receipt(path, receipt)
            if (
                output_dir is not None
                and job.status == "completed"
                and job.request_sha256 not in downloaded
            ):
                download_outputs(api, job, output_dir)
                downloaded.add(job.request_sha256)
                save_receipt(path, receipt)
        pending = any(job.status == "submitted" for job in receipt.jobs)
        if not pending or not wait:
            return not pending
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return False
        time.sleep(min(poll_interval, remaining))


def assignments(values: list[str]) -> dict[str, JsonValue]:
    result = {}
    for value in values:
        key, sep, raw = value.partition("=")
        if not sep or not key:
            raise ValueError("--set requires NAME=VALUE (VALUE may be JSON)")
        try:
            result[key] = json.loads(raw)
        except json.JSONDecodeError:
            result[key] = raw
    return result


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser. Exposed so offline tests can assert defaults."""

    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    submit = commands.add_parser("submit", help="One job, or prompts × images × seeds")
    submit.add_argument("workflow", type=Path)
    submit.add_argument("--prompt", action="append", default=[])
    submit.add_argument("--image", type=Path, action="append", default=[])
    submit.add_argument("--seed", type=int, action="append", default=[])
    submit.add_argument("--set", action="append", default=[], metavar="NAME=VALUE")
    batch = commands.add_parser("batch", help="Explicit jobs, including multi-image inputs")
    batch.add_argument("manifest", type=Path)
    collect = commands.add_parser("collect", help="Collect a saved batch without resubmitting")
    collect.add_argument("receipts", type=Path)
    for command in (submit, batch):
        command.add_argument(
            "--url",
            default=configured_comfy_url(),
            help=(
                "ComfyUI endpoint. Defaults to the first configured "
                "content.apis.stableforge.comfy_workers entry. Required when "
                "no worker is configured; there is no assumed default host."
            ),
        )
        command.add_argument("--receipts", type=Path, required=True)
        command.add_argument("--dry-run", action="store_true", help="Prepare receipts offline")
    for command in (submit, batch, collect):
        command.add_argument("--wait", action="store_true")
        command.add_argument("--timeout", type=float, default=3600, help="Wait budget in seconds")
        command.add_argument("--http-timeout", type=float, default=30)
        command.add_argument("--poll-interval", type=float, default=2)
        command.add_argument("--output-dir", type=Path, help="Download images outside the repo")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.timeout <= 0 or not 0 < args.poll_interval <= 60:
            raise ValueError("Timeout must be positive and poll interval must be in (0, 60]")
        # `collect` is exempt: it uses the endpoint bound to its receipt and
        # never defines --url. No host is assumed for the others; an
        # unreachable guess is no better than no worker at all.
        if hasattr(args, "url") and args.url is None:
            raise ValueError(
                "No ComfyUI worker configured. Set "
                "content.apis.stableforge.comfy_workers in settings.local.toml "
                "(gitignored), or an equivalent TANGL_ environment variable, or "
                "pass --url explicitly."
            )
        if args.output_dir and args.output_dir.resolve().is_relative_to(REPO_ROOT):
            raise ValueError("Download media outside the repository (PNG/JPG Git LFS safety)")
        if args.command == "collect":
            receipt = BatchReceipt.model_validate_json(args.receipts.read_text())
            api = ComfyApi(receipt.endpoint, timeout=args.http_timeout)
        else:
            api = ComfyApi(args.url, timeout=args.http_timeout)
            if args.command == "batch":
                manifest = BatchInput.model_validate_json(args.manifest.read_text())
                root = args.manifest.resolve().parent
                template = (root / manifest.workflow).read_text()
                jobs = [
                    JobInput(
                        params={**manifest.params, **job.params},
                        images={slot: root / source for slot, source in job.images.items()},
                    )
                    for job in manifest.jobs
                ]
            else:
                template = args.workflow.read_text()
                defaults = assignments(args.set)
                jobs = []
                for prompt, image, seed in itertools.product(
                    args.prompt or [None], args.image or [None], args.seed or [None]
                ):
                    params = dict(defaults)
                    if prompt is not None:
                        params["prompt"] = prompt
                    if seed is not None:
                        params["seed"] = seed
                    jobs.append(JobInput(params=params, images={"source": image} if image else {}))
            receipt = resume_receipt(
                args.receipts, prepare_jobs(template, jobs, api.endpoint())
            )
            if args.dry_run:
                print(receipt.model_dump_json(indent=2))
                return 0
            submit_jobs(api, receipt, args.receipts)
        complete = True
        if args.command == "collect" or args.wait or args.output_dir:
            complete = collect_jobs(
                api, receipt, args.receipts, wait=args.wait, timeout=args.timeout,
                poll_interval=args.poll_interval, output_dir=args.output_dir,
            )
        print(json.dumps({
            "receipts": str(args.receipts.resolve()),
            "jobs": [{"prompt_id": j.prompt_id, "status": j.status} for j in receipt.jobs],
        }))
        if any(
            j.status in {"failed", "rejected", "submitting", "submission_unknown"}
            for j in receipt.jobs
        ):
            return 1
        return 2 if args.wait and not complete else 0
    except (OSError, requests.RequestException, ValueError, TemplateError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("Stopped waiting/submitting; remote jobs were not cancelled.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
