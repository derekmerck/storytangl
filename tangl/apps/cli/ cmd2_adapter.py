from argparse import ArgumentParser
from cmd2 import CommandSet

from tangl.service.api_endpoints import HasApiEndpoints

class Cmd2Adapter:
    """Creates cmd2 commands from ServiceManager"""

    @classmethod
    def create_command_set(cls, service_manager: HasApiEndpoints):
        command_set = CommandSet()

        for name, endpoint in service_manager.get_api_endpoints().items():
            # Create command with appropriate parser
            parser = ArgumentParser()
            # Add args based on type hints
            command_set.add_command(name, parser, endpoint)

        return command_set