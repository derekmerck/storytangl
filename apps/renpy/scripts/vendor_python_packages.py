from __future__ import annotations

import argparse
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
        help="Host Python 3.12 interpreter used to run pip. Default: python3.12",
    )
    parser.add_argument(
        "--target",
        type=Path,
        default=Path("apps/renpy/project/game/python-packages"),
        help="Directory that will receive vendored packages.",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[3],
        help="StoryTangl repository root to install from.",
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

    pip_cmd = [binary, "-m", "pip", "--version"]
    try:
        subprocess.run(
            pip_cmd,
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        raise SystemExit(
            f"Host interpreter {binary!r} does not have a working pip: {exc.stderr.strip()}"
        ) from exc


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


def main() -> int:
    args = parse_args()
    repo_root = args.repo_root.resolve()
    target = args.target.resolve()
    python = _resolve_python(args.python)

    _check_python(python)

    target.mkdir(parents=True, exist_ok=True)
    if not args.keep_existing:
        _clear_target(target)

    install_cmd = [
        python,
        "-m",
        "pip",
        "install",
        "--upgrade",
        "--target",
        str(target),
        str(repo_root),
    ]

    print(f"Vendoring StoryTangl demo dependencies into {target}")
    print("Running:", " ".join(install_cmd))
    subprocess.run(install_cmd, check=True)
    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
