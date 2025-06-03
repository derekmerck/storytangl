import argparse
import logging
from typing import TYPE_CHECKING
from pprint import pformat

from cmd2 import with_argparser, with_default_category, CommandSet

# from tangl.service.request_models import ActionRequest
from tangl.journal import JournalItem, JournalEntry
from tangl.story.story_info_models import StoryInfo

from tangl.cli.app_service_manager import service_manager, user_id

if TYPE_CHECKING:
    from ..app import TanglShell

logger = logging.getLogger("tangl.cli")

@with_default_category('Story')
class StoryController(CommandSet):

    _cmd: 'TanglShell'

    def poutput(self, *args):
        self._cmd.poutput(*args)

    def __init__(self):
        super().__init__()
        self._current_story_update = None

    def _render_current_story_update(self):

        # def _render_image(image_id):
        #     width = shutil.get_terminal_size()[0]
        #     # xtodo: this may not work server-side with remote apis, may need to
        #     #       decode it to ansi locally?
        #     ansi_art = api.get_media(image_id, fmt="ansi", width=width )
        #     self.poutput(ansi_art)

        def _render_block(bl: JournalItem, starting_action: int = 0):
            self.poutput("Story Update:")
            self.poutput("-------------------------")
            label = bl.label
            if label:
                self.poutput(f"# {label}\n")
            text = bl.text
            if text:
                self.poutput(text + '\n')
            # images = bl.get("images", [])
            # if images:
            # for image_id in images:
            #     handle_image(image_id)
            actions = bl.actions
            if actions:
                for i, ac in enumerate(actions):
                    self.poutput(f"{i + starting_action + 1}. {ac.text} ({str(ac.uid)[0:6]})")

        starting_action = 0
        for block in self._current_story_update:
            _render_block(block, starting_action)
            if hasattr(block, "actions") and block.actions:
                starting_action += len( block.actions )

    def _get_action_id(self, which: int):
        actions = []
        for bl in self._current_story_update:
            if hasattr(bl, "actions") and bl.actions:
                actions.extend(bl.actions)
        return actions[ which - 1 ].uid

        # def handle_block(bl, starting_action=1):
        #     self.poutput("Story Update:")
        #     self.poutput("-------------------------")
        #     label = bl.label
        #     if label:
        #         self.poutput(f"# {label}\n")
        #     text = bl.text
        #     if text:
        #         self.poutput(text + '\n')
        #     # images = bl.get("images", [])
        #     # if images:
        #     # for image_id in images:
        #     #     handle_image(image_id)
        #     # bl.actions = bl.actions or []
        #     for i, ac in enumerate(bl.actions):
        #
        #         self.poutput(f"{i + starting_action}. {ac.text} ({str(ac.uid)[0:6]})")
        #
        # starting_action = 1
        # for bl in update:
        #     handle_block(bl, starting_action=starting_action)
        #     starting_action += len(bl.actions)

    def do_story(self, line = None):
        """
        Display the current story narrative and possible choices.
        """
        logger.debug("Invoking story update")
        self._current_story_update = service_manager.get_story_update(user_id)
        logger.debug(f"Received update: {self._current_story_update}")
        self._render_current_story_update()

    create_story_parser = argparse.ArgumentParser()
    create_story_parser.add_argument('action', type=int, help='Action ID to execute')

    @with_argparser(create_story_parser)
    def do_do(self, args):
        """
        Select one of the possible choices and advance the story narrative.

        :param choice: the list position of the choice selected
        """
        action_uid = self._get_action_id(args.action)
        self._current_story_update = service_manager.do_story_action(user_id, action_id=action_uid)
        self._render_current_story_update()

    def _render_status_response(self, response: StoryInfo):
        self.poutput("Story Status:")
        if isinstance(response, dict):
            self.poutput(pformat(response))
        elif isinstance(response, list):
            for status_item in response:
                self.poutput(f"{status_item.key}: {status_item.value} ({status_item.style_cls})")
        else:
            self.poutput(str(response))

    def do_status(self, line):
        """
        Display the current story status.
        """
        response = service_manager.get_story_info(user_id)
        self._render_status_response(response)

