"""Entry point for the Typer-based admin utility."""

from __future__ import annotations

from .app import run


def main() -> None:
    run()


if __name__ == "__main__":
    main()
