"""Entry point for ``python -m tangl.devref``."""

from __future__ import annotations

from .cli import run


def main() -> None:
    run()


if __name__ == "__main__":
    main()
