"""Rich CLI entry point for ``tangl-cli-rich``."""

from __future__ import annotations

from .app import create_cli_app


def main() -> None:
    app = create_cli_app(terminal_style="rich")
    app.cmdloop()


if __name__ == "__main__":
    main()
