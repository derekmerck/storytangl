from typing import TYPE_CHECKING
import argparse
from pprint import pformat

from cmd2 import CommandSet, with_argparser, with_default_category

from tangl.cli.app_service_manager import service_manager

if TYPE_CHECKING:
    from ..app import TanglShell

@with_default_category('World')
class WorldController(CommandSet):

    _cmd: 'TanglShell'

    def poutput(self, *args):
        self._cmd.poutput(*args)

    def do_worlds(self, line):
        response = service_manager.get_world_list()
        response = pformat(response)
        self.poutput("World List\n-----------")
        self.poutput( response )

    get_world_id_parser = argparse.ArgumentParser()
    get_world_id_parser.add_argument('world', type=str, help='World Id', default=None)

    @with_argparser(get_world_id_parser)
    def do_world_info(self, args):
        """
        Display the public info for the specified world.
        """
        response = service_manager.get_world_info(args.world)
        self.poutput("World Info\n-----------")
        response = pformat(response)
        self.poutput( response )

    @with_argparser(get_world_id_parser)
    def do_scenes(self, args):
        self.poutput("Scene List\n-----------")
        response = service_manager.get_scene_list(world_id=args.world)
        self.poutput(response)
