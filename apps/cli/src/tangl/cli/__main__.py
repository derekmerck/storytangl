"""CLI entry point for ``python -m tangl.cli``."""

from __future__ import annotations

import sys

from .app import create_cli_app


def main() -> None:
    app = create_cli_app()

    if not sys.stdin.isatty():
        app.onecmd_plus_hooks("quit")
        return

    app.cmdloop()


if __name__ == "__main__":
    main()
