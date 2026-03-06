from __future__ import annotations

from typing import TYPE_CHECKING

from cmd2 import CommandSet, with_default_category
from tangl.service import ServiceOperation38
from tangl.service.operations import endpoint_for_operation

if TYPE_CHECKING:
    from ..app import StoryTanglCLI


@with_default_category("System")
class SystemController(CommandSet):
    """Expose system-level orchestrated commands."""

    _cmd: StoryTanglCLI

    def _call_service(self, operation: ServiceOperation38):
        call_operation = getattr(self._cmd, "call_operation", None)
        if callable(call_operation):
            return call_operation(operation)
        return self._cmd.call_endpoint(endpoint_for_operation(operation))

    def do_system_info(self, _: str | None = None) -> None:  # noqa: ARG002 - cmd2 interface
        info = self._call_service(ServiceOperation38.SYSTEM_INFO)
        self._cmd.poutput(info)
