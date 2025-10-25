"""CLI entry point for ``python -m tangl.cli``."""

from __future__ import annotations

from .app import create_cli_app


def main() -> None:
    app = create_cli_app()
    app.cmdloop()


if __name__ == "__main__":
    main()
