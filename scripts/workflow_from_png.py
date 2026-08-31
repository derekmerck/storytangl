#!/usr/bin/env python3
"""Extract a ComfyUI workflow from PNG metadata and suggest template parameters.

ComfyUI embeds two tEXt chunks: ``prompt`` (API format, what comfy_batch.py
consumes) and, for UI-generated images, ``workflow`` (canvas layout). This reads
the API format and points at the inputs worth exposing as Jinja variables.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from PIL import Image

# Inputs almost always worth parameterizing, by input-name substring.
CANDIDATES = ("text", "seed", "width", "height", "steps", "filename_prefix", "image")


def extract(path: Path) -> tuple[dict, bool]:
    """Return the API-format workflow and whether a UI layout was also present."""
    info = Image.open(path).info
    if "prompt" not in info:
        raise SystemExit(f"{path}: no 'prompt' chunk — not a ComfyUI PNG, or metadata stripped")
    return json.loads(info["prompt"]), "workflow" in info


def suggest(workflow: dict) -> list[tuple[str, str, object]]:
    """Return (node_id, input_name, value) triples worth turning into variables."""
    found = []
    for node_id, node in sorted(workflow.items()):
        for name, value in node.get("inputs", {}).items():
            if isinstance(value, list):
                continue  # a wire to another node, not a literal
            if any(token in name.lower() for token in CANDIDATES):
                found.append((node_id, name, value))
    return found


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("png", type=Path)
    ap.add_argument("-o", "--out", type=Path, help="write the workflow JSON here")
    ap.add_argument("--models", action="store_true", help="list model files it depends on")
    args = ap.parse_args()

    workflow, has_layout = extract(args.png)
    print(f"{len(workflow)} nodes; UI layout chunk: {'present' if has_layout else 'absent'}")

    if args.models:
        for node_id, node in sorted(workflow.items()):
            for name, value in node.get("inputs", {}).items():
                if isinstance(value, str) and value.endswith((".safetensors", ".ckpt", ".pt", ".gguf")):
                    print(f"  model  {node_id}.{name} = {value}")

    print("\nCandidate template parameters:")
    for node_id, name, value in suggest(workflow):
        shown = json.dumps(value)
        print(f"  {node_id}.{name} = {shown[:88]}")

    if args.out:
        args.out.write_text(json.dumps(workflow, indent=2) + "\n")
        print(f"\nwrote {args.out}")
        print("Rename to .json.j2 and replace the values above with Jinja, e.g.")
        print('  "text": {{ prompt | tojson }}      "noise_seed": {{ seed }}')
    else:
        print("\n(pass -o to write the workflow; stdout stays a summary)", file=sys.stderr)


if __name__ == "__main__":
    main()
