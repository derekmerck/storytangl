import cmd2

from tangl.service.api_endpoints import ServiceManager
from tangl.business.story.story_controller import StoryController
from tangl.service.user.user_controller import UserController
from .cmd2_adapter import Cmd2Adapter


class TanglSh(cmd2.Cmd):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Build or retrieve the service manager
        sm = ServiceManager(context={}, components=[StoryController, UserController])

        # Create the command set
        adapter = Cmd2Adapter(sm)
        cmdset = adapter.create_command_set()

        # Add that command set to our shell
        self.add_command_set(cmdset)


if __name__ == "__main__":
    app = TanglSh()
    app.cmdloop()
