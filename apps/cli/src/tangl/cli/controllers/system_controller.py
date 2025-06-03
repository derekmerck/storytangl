from typing import TYPE_CHECKING
import argparse
from pprint import pformat

from cmd2 import CommandSet, with_default_category

from tangl.cli.app_service_manager import service_manager

if TYPE_CHECKING:
    from ..app import TanglShell

@with_default_category('System')
class SystemController(CommandSet):

    _cmd: 'TanglShell'

    def poutput(self, *args):
        self._cmd.poutput(*args)

    def do_system_info(self, line):
        """
        Display the current status of the service backend.
        """
        info = service_manager.get_system_info()
        self.poutput(info)
