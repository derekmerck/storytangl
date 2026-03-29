#!/usr/bin/env python3
"""Smoke test a real ComfyUI worker with the packaged StoryTangl workflow."""

from __future__ import annotations

import argparse
import io
import sys
import time
from pathlib import Path

from PIL import Image

from tangl.media.media_creators.comfy_forge import ComfyApi, ComfyDispatcher, ComfySpec


def list_models(api: ComfyApi) -> None:
    snapshot = api.describe_worker(model_folders=("checkpoints", "loras", "vae"))
    print(f"ComfyUI at {api.endpoint()}")
    print(f"  System: {snapshot.system_stats.get('system', {}).get('os', '?')}")
    for folder, models in snapshot.models_by_folder.items():
        print(f"\n  {folder}:")
        for model_name in models:
            print(f"    - {model_name}")
    if snapshot.embeddings:
        print(f"\n  embeddings: {', '.join(snapshot.embeddings[:10])}")
        if len(snapshot.embeddings) > 10:
            print(f"    ... and {len(snapshot.embeddings) - 10} more")


def _select_checkpoint(api: ComfyApi, checkpoint: str | None) -> str:
    if checkpoint is not None:
        return checkpoint
    models = api.list_models("checkpoints")
    if not models:
        raise RuntimeError("No checkpoints found on worker; pass --checkpoint or install one.")
    return models[0]


def smoke_test(
    *,
    url: str,
    checkpoint: str | None,
    prompt: str,
    output: str,
    timeout: float,
) -> None:
    api = ComfyApi(url)
    checkpoint_name = _select_checkpoint(api, checkpoint)
    spec = ComfySpec(
        workflow_template="portrait_txt2img",
        prompt=prompt,
        n_prompt="low quality, blurry, bad anatomy, worst quality",
        model=checkpoint_name,
        seed=42,
        dims=(512, 768),
        iterations=20,
    )
    adapted_payload = spec.normalized_spec_payload()

    print(f"\nSubmitting to {api.endpoint()} ...")
    print(f"  checkpoint: {checkpoint_name}")
    print(f"  prompt:     {prompt}")
    print("  dims:       512x768")
    print("  steps:      20")

    dispatcher = ComfyDispatcher(url=url, api=api)
    job_id = dispatcher.submit(adapted_payload)
    print(f"  job_id:     {job_id}")

    started_at = time.time()
    deadline = started_at + timeout
    result = None
    while time.time() < deadline:
        result = dispatcher.poll(job_id)
        if result is not None:
            break
        elapsed = int(time.time() - started_at)
        print(f"  polling... ({elapsed}s)", end="\r")
        time.sleep(2.0)
    else:
        raise TimeoutError(f"Timed out after {timeout}s waiting for ComfyUI output")

    print()
    if not result.success:
        raise RuntimeError(f"Comfy smoke test failed: {result.error}")

    image = Image.open(io.BytesIO(result.data))
    out_path = Path(output)
    image.save(out_path)
    print(f"SUCCESS: {image.size[0]}x{image.size[1]} image saved to {out_path}")


def main() -> int:
    parser = argparse.ArgumentParser(description="ComfyUI smoke test")
    parser.add_argument("--url", default="http://127.0.0.1:8188", help="ComfyUI endpoint")
    parser.add_argument("--checkpoint", default=None, help="Checkpoint filename")
    parser.add_argument(
        "--prompt",
        default="portrait of a young woman with navy hair, punk hairstyle, steampunk",
        help="Positive prompt",
    )
    parser.add_argument("--output", default="comfy_smoke_test.png", help="Output image path")
    parser.add_argument("--timeout", type=float, default=120.0, help="Timeout in seconds")
    parser.add_argument("--list-models", action="store_true", help="List available models and exit")
    args = parser.parse_args()

    try:
        if args.list_models:
            list_models(ComfyApi(args.url))
            return 0
        smoke_test(
            url=args.url,
            checkpoint=args.checkpoint,
            prompt=args.prompt,
            output=args.output,
            timeout=args.timeout,
        )
        return 0
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
