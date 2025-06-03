from typing import TYPE_CHECKING
from cmd2 import CommandSet, with_argparser, with_default_category
import argparse

import tangl.cli.app_service_manager
from tangl.cli.app_service_manager import service_manager, user_id

if TYPE_CHECKING:
    from ..app import TanglShell

@with_default_category('User')
class UserController(CommandSet):

    _cmd: 'TanglShell'

    def poutput(self, *args):
        self._cmd.poutput(*args)

    # Public

    get_secret_parser = argparse.ArgumentParser()
    get_secret_parser.add_argument('secret', type=str, help='Secret for the user')

    @with_argparser(get_secret_parser)
    def create_user(self, args):
        """
        Create a new user and set the current user's ID.
        """
        secret = args.secret
        new_user_id, secret = service_manager.create_user(secret)
        tangl.cli.app_service_manager.user_id = new_user_id
        self.poutput(f'User created with ID: {user_id} and secret: {secret}')

    @with_argparser(get_secret_parser)
    def key(self, args):
        secret = args.secret
        response = service_manager.key_for_secret(secret)
        self.poutput(response)

    # Client

    @with_argparser(get_secret_parser)
    def do_change_secret(self, args):
        """
        Change the current user's secret and get a new ID.
        """
        secret = args.secret
        new_user_id, secret = service_manager.update_user_secret(user_id, secret)
        tangl.cli.app_service_manager.user_id = new_user_id
        self.poutput(f'User secret changed to: {secret}\nNew user ID: {self.user_id}')

    def do_drop_user(self, line):
        """
        Drop this user and all of their stories.
        """
        service_manager.remove_user(user_id)
        tangl.cli.app_service_manager.user_id = None
        self.poutput('User dropped.')

    get_world_id_parser = argparse.ArgumentParser()
    get_world_id_parser.add_argument('world_id', type=str, help='World Id')

    @with_argparser(get_world_id_parser)
    def do_set_story(self, args):
        """
        Change to the specified story world for the current user.
        """
        world_id = args.world_id
        service_manager.set_current_story_id(user_id, world_id=world_id)
        self.poutput(f'Story world set to: {world_id}')

    @with_argparser(get_world_id_parser)
    def do_create_story(self, args):
        """
        Create a new story from the specified world for the current user.
        """
        service_manager.create_story(user_id, world_id=args.world_id)
        # service_manager.set_current_story_id(user_id, args.world_id)
        from .story_controller import StoryController
        # self._cmd._current_story_update = service_manager.get_story_update(user_id)
        # self._cmd._render_current_story_update()
        self._cmd.do_story()
