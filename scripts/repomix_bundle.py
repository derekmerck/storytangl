#!/usr/bin/env python3
"""Generate curated Repomix bundles for StoryTangl."""

from __future__ import annotations

import argparse
import json
import shlex
import shutil
import subprocess
import sys
from dataclasses import dataclass, replace
from datetime import datetime
from pathlib import Path
from typing import Iterable


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT_DIR = REPO_ROOT / "tmp" / "repomix"
STYLE_EXTENSIONS = {
    "markdown": "md",
    "json": "json",
    "plain": "txt",
    "xml": "xml",
}

COMMON_IGNORES = (
    ".github/**",
    ".githooks/**",
    "carwars-gamebooks/**",
    "scratch/**",
    "tmp/**",
    "sdks/**",
    "node_modules/**",
    "**/*.png",
    "**/*.jpg",
    "**/*.jpeg",
    "**/*.webp",
    "**/*.gif",
    "**/*.bmp",
    "**/*.mp3",
    "**/*.wav",
    "**/*.ogg",
    "**/*.mp4",
    "**/*.mov",
    "**/*.avi",
    "**/*.zip",
    "**/*.tar",
    "**/*.tgz",
    "**/*.gz",
    "**/*.pdf",
)


@dataclass(frozen=True)
class Bundle:
    name: str
    description: str
    include: tuple[str, ...]
    ignore: tuple[str, ...] = ()
    style: str = "markdown"
    compress: bool = True
    remove_comments: bool = True
    remove_empty_lines: bool = False
    no_files: bool = False

    def output_name(self) -> str:
        ext = STYLE_EXTENSIONS[self.style]
        return f"{self.name}.{ext}"


def _merge_patterns(*groups: Iterable[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    merged: list[str] = []
    for group in groups:
        for pattern in group:
            if pattern in seen:
                continue
            seen.add(pattern)
            merged.append(pattern)
    return tuple(merged)


BUNDLES: dict[str, Bundle] = {
    "foundation": Bundle(
        name="foundation",
        description="Core runtime layers: core, vm, story, and journal.",
        include=(
            "AGENTS.md",
            "ARCHITECTURE.md",
            "engine/src/tangl/__init__.py",
            "engine/src/tangl/exceptions.py",
            "engine/src/tangl/info.py",
            "engine/src/tangl/type_hints.py",
            "engine/src/tangl/core/**/*.py",
            "engine/src/tangl/vm/**/*.py",
            "engine/src/tangl/story/**/*.py",
            "engine/src/tangl/journal/**/*.py",
        ),
    ),
    "service-persistence": Bundle(
        name="service-persistence",
        description="Service, persistence, server, CLI, and runtime configuration.",
        include=(
            "pyproject.toml",
            "settings.toml",
            "engine/src/tangl/config.py",
            "engine/src/tangl/defaults.toml",
            "engine/src/tangl/persistence/**/*.py",
            "engine/src/tangl/service/**/*.py",
            "apps/cli/src/**/*.py",
            "apps/server/src/**/*.py",
            "deployment/docker/**/*",
        ),
    ),
    "mechanics-media-prose": Bundle(
        name="mechanics-media-prose",
        description="Mechanics, media, prose, and language subsystems.",
        include=(
            "engine/src/tangl/lang/**/*.py",
            "engine/src/tangl/mechanics/**/*.py",
            "engine/src/tangl/media/**/*.py",
            "engine/src/tangl/media/**/*.json",
            "engine/src/tangl/prose/**/*.py",
        ),
    ),
    "apps": Bundle(
        name="apps",
        description="Application entry points and frontend/server clients.",
        include=(
            "apps/**/AGENTS.md",
            "apps/cli/src/**/*.py",
            "apps/renpy/project/game/**/*.rpy",
            "apps/renpy/scripts/**/*.py",
            "apps/renpy/scripts/**/*.sh",
            "apps/renpy/src/**/*.py",
            "apps/server/src/**/*.py",
            "apps/web/.env.example",
            "apps/web/eslint.config.js",
            "apps/web/index.html",
            "apps/web/package.json",
            "apps/web/public/**/*.js",
            "apps/web/src/**/*.css",
            "apps/web/src/**/*.scss",
            "apps/web/src/**/*.ts",
            "apps/web/src/**/*.vue",
            "apps/web/tsconfig*.json",
            "apps/web/vite.config.ts",
        ),
    ),
    "docs-index": Bundle(
        name="docs-index",
        description="Index-only bundle for design docs, notes, and contributor guidance.",
        include=(
            "AGENTS.md",
            "ARCHITECTURE.md",
            "README.md",
            "VERSIONS.md",
            "engine/tests/AGENTS.md",
            "docs/**/*.md",
            "docs/**/*.py",
            "docs/**/*.rst",
            "engine/src/**/*_DESIGN.md",
            "engine/src/**/notes.md",
            "apps/**/AGENTS.md",
            "apps/**/notes/**",
        ),
        style="json",
        compress=False,
        remove_comments=False,
        no_files=True,
    ),
}

BUNDLES["repo-index"] = Bundle(
    name="repo-index",
    description="Index-only bundle covering all curated code and docs slices.",
    include=_merge_patterns(*(bundle.include for bundle in BUNDLES.values())),
    style="json",
    compress=False,
    remove_comments=False,
    no_files=True,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "bundles",
        nargs="*",
        help="Bundle names to generate. Use --all or --list to discover presets.",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Generate every curated bundle.",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available bundle names and exit.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Destination directory. Default: {DEFAULT_OUTPUT_DIR}",
    )
    parser.add_argument(
        "--repomix-bin",
        default="repomix",
        help="Repomix executable to invoke.",
    )
    parser.add_argument(
        "--style",
        choices=tuple(STYLE_EXTENSIONS),
        help="Override output style for all selected bundles.",
    )
    parser.add_argument(
        "--no-compress",
        action="store_true",
        help="Disable structural compression for all selected bundles.",
    )
    parser.add_argument(
        "--keep-comments",
        action="store_true",
        help="Retain code comments in all selected bundles.",
    )
    parser.add_argument(
        "--remove-empty-lines",
        action="store_true",
        help="Strip blank lines from all selected bundles.",
    )
    parser.add_argument(
        "--token-count-tree",
        nargs="?",
        const="0",
        metavar="THRESHOLD",
        help="Forward --token-count-tree to repomix for each bundle.",
    )
    parser.add_argument(
        "--top-files-len",
        type=int,
        default=10,
        help="Number of large files repomix should show in its summary.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print commands without executing them.",
    )
    return parser


def resolve_bundles(args: argparse.Namespace) -> list[Bundle]:
    if args.all:
        names = list(BUNDLES)
    else:
        names = args.bundles

    if not names:
        raise SystemExit("Choose at least one bundle, or use --all / --list.")

    unknown = [name for name in names if name not in BUNDLES]
    if unknown:
        raise SystemExit(f"Unknown bundle(s): {', '.join(unknown)}")

    bundles: list[Bundle] = []
    for name in names:
        bundle = BUNDLES[name]
        if args.style:
            bundle = replace(bundle, style=args.style)
        if args.no_compress:
            bundle = replace(bundle, compress=False)
        if args.keep_comments:
            bundle = replace(bundle, remove_comments=False)
        if args.remove_empty_lines:
            bundle = replace(bundle, remove_empty_lines=True)
        bundles.append(bundle)
    return bundles


def build_command(
    bundle: Bundle,
    output_dir: Path,
    repomix_bin: str,
    token_count_tree: str | None,
    top_files_len: int,
) -> tuple[list[str], Path]:
    output_path = output_dir / bundle.output_name()
    cmd = [
        repomix_bin,
        ".",
        "--output",
        str(output_path),
        "--style",
        bundle.style,
        "--top-files-len",
        str(top_files_len),
    ]

    if bundle.include:
        cmd.extend(["--include", ",".join(bundle.include)])

    ignore_patterns = _merge_patterns(COMMON_IGNORES, bundle.ignore)
    if ignore_patterns:
        cmd.extend(["--ignore", ",".join(ignore_patterns)])

    if bundle.no_files:
        cmd.append("--no-files")
    elif bundle.compress:
        cmd.append("--compress")

    if bundle.remove_comments:
        cmd.append("--remove-comments")

    if bundle.remove_empty_lines:
        cmd.append("--remove-empty-lines")

    if token_count_tree is not None:
        cmd.extend(["--token-count-tree", token_count_tree])

    return cmd, output_path


def write_manifest(
    output_dir: Path,
    generated: list[tuple[Bundle, Path]],
) -> Path:
    manifest_path = output_dir / "manifest.json"
    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "repo_root": str(REPO_ROOT),
        "bundles": [
            {
                "name": bundle.name,
                "description": bundle.description,
                "path": str(path),
                "style": bundle.style,
                "compress": bundle.compress,
                "remove_comments": bundle.remove_comments,
                "remove_empty_lines": bundle.remove_empty_lines,
                "no_files": bundle.no_files,
            }
            for bundle, path in generated
        ],
    }
    manifest_path.write_text(json.dumps(payload, indent=2) + "\n")
    return manifest_path


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.list:
        for bundle in BUNDLES.values():
            print(f"{bundle.name:24} {bundle.description}")
        return 0

    if shutil.which(args.repomix_bin) is None:
        raise SystemExit(f"Repomix executable not found: {args.repomix_bin}")

    bundles = resolve_bundles(args)
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    generated: list[tuple[Bundle, Path]] = []
    for bundle in bundles:
        cmd, output_path = build_command(
            bundle=bundle,
            output_dir=output_dir,
            repomix_bin=args.repomix_bin,
            token_count_tree=args.token_count_tree,
            top_files_len=args.top_files_len,
        )
        print(shlex.join(cmd), flush=True)
        if args.dry_run:
            continue
        subprocess.run(cmd, cwd=REPO_ROOT, check=True)
        generated.append((bundle, output_path))

    if args.dry_run:
        return 0

    manifest_path = write_manifest(output_dir, generated)
    print(f"Wrote manifest: {manifest_path}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as exc:
        print(f"Repomix failed with exit code {exc.returncode}", file=sys.stderr)
        raise SystemExit(exc.returncode)
