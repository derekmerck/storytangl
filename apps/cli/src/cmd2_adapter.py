import argparse
import inspect
from cmd2 import CommandSet, with_argparser
from typing import Optional, get_type_hints
from uuid import UUID

from tangl.service.api_endpoint import HasApiEndpoints, ApiEndpoint, MethodType, AccessLevel, ServiceManager


class Cmd2Adapter:
    """
    Creates a Cmd2 CommandSet from a ServiceManager by reflecting each endpoint.

    Basic logic:
    - For each endpoint, build a dynamic cmd2 command name 
      (like "do_get_story_info" => "get_story_info" or just "story_info")
    - Create an ArgumentParser from the type hints (if you want more advanced arg parsing)
    - In the command function, parse arguments, possibly decode user_id, call the manager endpoint,
      and display the result.
    """

    def __init__(self, service_manager: ServiceManager):
        self.service_manager = service_manager

    def create_command_set(self) -> CommandSet:
        """
        Build a single CommandSet that has commands for all endpoints in the service_manager.

        :return: A CommandSet that can be added to your cmd2 app with `app.add_command(cmdset)`.
        """
        cmdset = CommandSet()

        # We reflect over each endpoint
        for name, func in self.service_manager.endpoints.items():
            api_ep: ApiEndpoint = getattr(func, "_api_endpoint", None)
            if not api_ep:
                continue  # skip if no metadata

            command_name = self._mangle_command_name(api_ep)
            parser = self._build_argparser(api_ep)
            # We create a dynamic method for the command
            method = self._make_command_method(api_ep, func, parser)

            # Attach the parser with the "with_argparser" decorator
            wrapped_method = with_argparser(parser)(method)
            # Set the category or help text if you want:
            wrapped_method.__doc__ = f"{api_ep.method_type.value.upper()} {api_ep.name} (group={api_ep.group})"

            # Now add that command to the CommandSet
            cmdset.add_command(wrapped_method, command_name)

        return cmdset

    def _mangle_command_name(self, api_ep: ApiEndpoint) -> str:
        """
        Convert something like 'get_story_info' to 'story_info', or drop the prefix.
        Possibly drop the group prefix as well, e.g. 'story_info' -> 'info'.
        You might also incorporate the group name so that user commands don't collide with story commands, etc.
        """
        cmd_name = api_ep.name

        # drop known prefixes
        for prefix in ["get_", "create_", "drop_", "update_", "do_"]:
            if cmd_name.startswith(prefix):
                cmd_name = cmd_name[len(prefix):]
                break

        # if group = story, maybe drop that from the front if it matches?
        if api_ep.group and cmd_name.startswith(api_ep.group + "_"):
            cmd_name = cmd_name[len(api_ep.group) + 1:]

        return cmd_name.lower().replace("_", "-")

    def _build_argparser(self, api_ep: ApiEndpoint) -> argparse.ArgumentParser:
        """
        Construct an ArgumentParser by reading the function's type hints.
        This is optional or minimal: you might not want to auto-parse everything, 
        or you might want more advanced logic.
        """
        parser = argparse.ArgumentParser(prog=api_ep.name, description=f"{api_ep.method_type} {api_ep.name}")
        hints = api_ep.type_hints()
        # e.g. hints = {'story': Story, 'media': Union[MediaRecord, Identifier], 'return': ...}
        # build arguments from that
        # For demonstration, let's handle 'user_id' if needed:
        if api_ep.access_level > AccessLevel.PUBLIC:
            # user_id required
            parser.add_argument("--user_id", type=str, help="User ID or x-auth token")

        # For the rest, you might do something like scanning the hints for non-Story param
        # but let's keep it minimal
        return parser

    def _make_command_method(self, api_ep: ApiEndpoint, manager_func, parser: argparse.ArgumentParser):
        """
        Build the function that cmd2 will call. It must accept (self, args).
        `args` is the result of parser.parse_args.
        We'll parse user_id if needed, pass everything else to the manager function.
        """

        def command_method(_self, args):
            """
            The actual code that runs when the user types the command in cmd2.
            `_self` is the cmd2 app instance (with poutput, etc.).
            `args` is the parsed arguments from argparser.
            """
            # user_id logic
            kwargs = {}
            if api_ep.access_level > AccessLevel.PUBLIC:
                if not args.user_id:
                    _self.perror("Must supply --user_id for restricted commands.")
                    return
                # decode or parse the user_id
                # possibly you do: user_id = decode_token(args.user_id)
                # or just treat it as a string:
                kwargs["user_id"] = args.user_id

            # Now call the manager function
            result = manager_func(**kwargs)
            # Display the result
            if isinstance(result, dict) or isinstance(result, list):
                _self.poutput(str(result))
            else:
                _self.poutput(f"{result}")

        return command_method
