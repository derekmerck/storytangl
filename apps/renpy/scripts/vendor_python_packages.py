from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Vendor StoryTangl demo dependencies for the Ren'Py mac demo.",
    )
    parser.add_argument(
        "--python",
        default="python3.12",
        help="Host Python 3.12 interpreter whose site-packages will be copied. Default: python3.12",
    )
    parser.add_argument(
        "--target",
        type=Path,
        default=Path("apps/renpy/project/game/python-packages"),
        help="Directory that will receive copied packages.",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[3],
        help="StoryTangl repository root that will be added to a local .pth file.",
    )
    parser.add_argument(
        "--keep-existing",
        action="store_true",
        help="Do not clear the target directory before installing.",
    )
    return parser.parse_args()


def _resolve_python(binary: str) -> str:
    resolved = shutil.which(binary)
    if resolved is None:
        raise SystemExit(
            f"Could not find host interpreter '{binary}'. "
            "Install Python 3.12 and rerun with --python /path/to/python3.12."
        )
    return resolved


def _check_python(binary: str) -> None:
    version_cmd = [
        binary,
        "-c",
        "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')",
    ]
    result = subprocess.run(
        version_cmd,
        check=True,
        capture_output=True,
        text=True,
    )
    version = result.stdout.strip()
    if version != "3.12":
        raise SystemExit(
            f"Host interpreter {binary!r} is Python {version}, but Ren'Py 8.5.2 embeds Python 3.12. "
            "Use a Python 3.12 interpreter for vendoring native dependencies."
        )


def _clear_target(target: Path) -> None:
    if not target.exists():
        return

    for child in target.iterdir():
        if child.name == ".gitignore":
            continue
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()


def _resolve_site_packages(binary: str) -> Path:
    site_cmd = [
        binary,
        "-c",
        "import json, site; print(json.dumps(site.getsitepackages()))",
    ]
    result = subprocess.run(
        site_cmd,
        check=True,
        capture_output=True,
        text=True,
    )
    entries = json.loads(result.stdout.strip())
    for entry in entries:
        path = Path(entry)
        if path.exists():
            return path
    raise SystemExit(f"Could not resolve a site-packages directory for {binary!r}.")


def _copy_dependency_tree(source: Path, target: Path) -> None:
    for child in source.iterdir():
        if child.name == "__pycache__":
            continue
        if child.name.startswith("storytangl"):
            continue
        destination = target / child.name
        if child.is_dir():
            shutil.copytree(child, destination, dirs_exist_ok=True)
        else:
            shutil.copy2(child, destination)


def _write_local_pth(repo_root: Path, target: Path) -> None:
    pth_path = target / "storytangl_local.pth"
    pth_path.write_text(
        "\n".join(
            [
                str((repo_root / "apps/renpy/src").resolve()),
                str((repo_root / "engine/src").resolve()),
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def main() -> int:
    args = parse_args()
    repo_root = args.repo_root.resolve()
    target = args.target.resolve()
    python = _resolve_python(args.python)
    site_packages = _resolve_site_packages(python)

    _check_python(python)

    target.mkdir(parents=True, exist_ok=True)
    if not args.keep_existing:
        _clear_target(target)

    print(f"Vendoring StoryTangl demo dependencies into {target}")
    print(f"Copying dependencies from {site_packages}")
    _copy_dependency_tree(site_packages, target)
    _write_local_pth(repo_root, target)
    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
