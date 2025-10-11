from __future__ import annotations

from typing import TYPE_CHECKING

from cmd2 import CommandSet, with_default_category

if TYPE_CHECKING:
    from ..app import StoryTanglCLI


@with_default_category("System")
class SystemController(CommandSet):
    """Expose system-level orchestrated commands."""

    _cmd: StoryTanglCLI

    def do_system_info(self, _: str | None = None) -> None:  # noqa: ARG002 - cmd2 interface
        info = self._cmd.call_endpoint("SystemController.get_system_info")
        self._cmd.poutput(info)
