from typing import TYPE_CHECKING
import argparse

from cmd2 import CommandSet, with_default_category, with_argparser

from tangl.cli.app_service_manager import service_manager, user_id

if TYPE_CHECKING:
    from ..app import TanglShell

@with_default_category('Restricted')
class DevController(CommandSet):

    _cmd: 'TanglShell'

    def poutput(self, *args):
        self._cmd.poutput(*args)

    # ----------
    # Story
    # ----------

    get_node_id = argparse.ArgumentParser()
    get_node_id.add_argument('node_id', type=str, help='Node id')

    @with_argparser(get_node_id)
    def do_inspect(self, args):
        node_id = args.node_id
        response = service_manager.get_node_info(user_id, node_id)
        self.poutput(f"Node Info {node_id}\n-----------")
        self.poutput(response)

    @with_argparser(get_node_id)
    def do_goto_node(self, args):
        node_id = args.node_id
        response = service_manager.goto_story_node(user_id, node_id)
        from tangl.cli.controllers import StoryController
        StoryController._render_current_story_update( self, response )

    get_expr_parser = argparse.ArgumentParser()
    get_expr_parser.add_argument('expr', type=str, help='Expression to check or apply')

    @with_argparser(get_expr_parser)
    def do_check(self, args):
        expr = args.expr
        response = service_manager.check_story_expr(user_id, expr=expr)
        self.poutput("Check expr\n-----------")
        self.poutput(response)

    @with_argparser(get_expr_parser)
    def do_apply(self, args):
        expr = args.expr
        response = service_manager.apply_story_expr(user_id, expr=expr)
        self.poutput("Apply effect\n-----------")
        self.poutput(response)
