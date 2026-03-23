from __future__ import annotations

from typing import TYPE_CHECKING

from cmd2 import CommandSet, with_default_category

if TYPE_CHECKING:
    from ..app import StoryTanglCLI


@with_default_category("System")
class SystemController(CommandSet):
    """Expose system-level manager-backed commands."""

    _cmd: StoryTanglCLI

    def _call_service(self, method_name: str):
        return self._cmd.call_service(method_name)

    def do_system_info(self, _: str | None = None) -> None:  # noqa: ARG002 - cmd2 interface
        info = self._call_service("get_system_info")
        self._cmd.poutput(info)
