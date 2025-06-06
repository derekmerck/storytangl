from __future__ import annotations
from typing import Type, TYPE_CHECKING
from contextlib import contextmanager
import functools
import inspect
from uuid import UUID

from .api_endpoint import HasApiEndpoints, ApiEndpoint, MethodType, AccessLevel

if TYPE_CHECKING:
    from tangl.story.story import Story
    from tangl.service.user import User

class ServiceManager:
    """
    Central class for injecting context and enforcing access levels
    across multiple controllers.

    The ServiceManager aggregates endpoints from one or more
    :class:`HasApiEndpoints` components, then wraps those methods in
    context managers that open (and optionally write back) domain objects
    like users or stories.

    **Motivation**:

    - Avoid duplicating “open an object from the store, link a user” logic
      in every method.
    - Provide a single place to check ACLs (access levels) and either
      allow or disallow method calls.
    - Make it easy to add new domain controllers. You just call
      :meth:`.add_component`, and the manager auto-registers their endpoints.

    **Usage**:

    .. code-block:: python

        sm = ServiceManager(context=my_data_store, components=[UserController, StoryController])

        # Suppose we have an endpoint named "StoryController.get_story_info"
        endpoint = sm.endpoints["StoryController.get_story_info"]
        result = endpoint(user_id=some_user_id)

        # The manager opens the user+story from context, checks ACL, calls the underlying method.

    :param context:
        A dictionary or other store containing loaded objects (e.g., user, story).
        The keys are typically UUIDs, and the values are domain objects.
    :param components:
        Optional list of controller classes (subclassing :class:`HasApiEndpoints`) or their instances.
        The manager automatically scans each for annotated endpoints and registers them.
    """
    def __init__(self, context=None, components=None):
        """
        Initializes the service manager with an optional ``context`` store
        and a list of components to register.
        """
        # The "context" might be a dict or a more sophisticated store
        self.context = context or {}
        self.components = components or []

        # We'll gather endpoints from each component
        # Each "component" can be either a class or an instance.
        self.endpoints = {}  # e.g. { 'get_world_info': <some bound method> }

        for comp in self.components:
            self.add_component(comp)

    def add_component(self, component: HasApiEndpoints | Type[HasApiEndpoints]):
        """
        Reflects over the given component to find annotated endpoints and
        wraps each with a context injection layer.

        :param component:
            Either an instance or a class that inherits :class:`HasApiEndpoints`.
        """
        # If component is a class, instantiate it, or vice versa.
        # Or maybe your pattern is that each component is already a class instance:
        if inspect.isclass(component):
            component_instance = component()
        else:
            component_instance = component

        endpoints = component_instance.get_api_endpoints()
        for method_name, api_endpoint in endpoints.items():
            # Let's define a "bound" callable that includes context injection
            bound_name = f"{component_instance.__class__.__name__}.{method_name}"
            wrapped_call = self._bind_endpoint(api_endpoint, component_instance)
            self.endpoints[bound_name] = wrapped_call

    @contextmanager
    def open_story(self, user_id: UUID, write_back: bool = False, write_back_user: bool = None, acl: AccessLevel = None) -> 'Story':
        """
        Opens a user's current story from :attr:`context`, linking the story.user
        field to the user object. Optionally writes the story (and user) back on exit.

        :param user_id: The UUID of the user whose story we want to open.
        :param write_back: If True, the story is written back to the context on exit.
        :param write_back_user: If set, determines whether the user is written back.
                                Defaults to the same value as ``write_back`` if not provided.
        :param acl: Required access level for this operation.
        :return: Yields a story-like object from the store.
        """
        if write_back_user is None:
            write_back_user = write_back
        with self.open_user(user_id, write_back=write_back_user, acl=acl) as user:
            story = self.context[user.current_story_id]
            story.user = user
            yield story
            if write_back:
                story.user = user.uid
                self.context[story.uid] = story

    @contextmanager
    def open_user(self, user_id: UUID, write_back: bool = False, acl: AccessLevel = None) -> 'User':
        """
        Context manager that fetches a user from :attr:`context`, optionally checks ACL,
        and writes the user back if ``write_back=True``.

        :param user_id: The UUID of the user object in the context store.
        :param write_back: If True, modifies :attr:`context` with updated user info on exit.
        :param acl: Required access level for this operation. Raises ``RuntimeError`` if user < acl.
        :return: Yields a user-like object from the store.
        :raises RuntimeError: If user's ``access_level`` is less than required ``acl``.
        """
        user = self.context[user_id]
        if acl and user.access_level < acl:
            raise RuntimeError(f"User acl {user.access_level} exceeds method acl {acl}")
        yield user
        if write_back:
            self.context[user.uid] = user

    def _bind_endpoint(self, api_endpoint: ApiEndpoint, component_instance):
        """
        Wraps the underlying method call with context injection logic
        (e.g., opening a user or story, verifying ACL, etc.).

        :param api_endpoint:
            The :class:`ApiEndpoint` metadata describing the target function.
        :param component_instance:
            The instance of the controller (subclass of :class:`HasApiEndpoints`) holding the method.
        :return: A callable that enforces the context logic and then calls the original method.
        """

        @functools.wraps(api_endpoint.func)
        def wrapper(*args,
                    user_id: UUID = None,  # replaces "story: Story" or "user: User" or required for ACL
                    **kwargs):
            """
            Wrapper function that intercepts calls, opens required contexts,
            checks access levels, and delegates to the original function.
            """

            if api_endpoint.access_level > AccessLevel.PUBLIC:
                if not user_id:
                    raise ValueError(f"user_id is required for {api_endpoint.name}")

                if "story" in api_endpoint.type_hints():
                    # Need to dereference the user, find the current story, and relink them

                    match api_endpoint.method_type:
                        case MethodType.READ | MethodType.UPDATE:
                            with self.open_story(user_id,
                                                 write_back=api_endpoint.method_type is MethodType.UPDATE,
                                                 acl=api_endpoint.access_level) as story:
                                # call the func and return the result
                                return api_endpoint(component_instance, *args, story=story, **kwargs)

                        case MethodType.DELETE:
                            with self.open_story(user_id,
                                                 write_back=False,      # don't write-back the story
                                                 write_back_user=True,  # do write-back the unlinked user
                                                 acl=api_endpoint.access_level) as story:
                                items_to_drop = api_endpoint(component_instance, story=story, *args, **kwargs) or []
                            for item_id in items_to_drop:
                                del self.context[item_id]
                            return items_to_drop

                        case _:
                            raise ValueError(f"Unsupported method type for story method: {api_endpoint.method_type}")

                elif "user" in api_endpoint.type_hints():
                    # Don't need to dereference a story, just the user

                    match api_endpoint.method_type:
                        case MethodType.READ | MethodType.UPDATE:
                            with self.open_user(user_id,
                                                write_back=api_endpoint.method_type is MethodType.UPDATE,
                                                acl=api_endpoint.access_level) as user:
                                # call the func and return the result
                                return api_endpoint(component_instance, *args, user=user, **kwargs)

                        case MethodType.DELETE:
                            with self.open_user(user_id, acl=api_endpoint.access_level) as user:
                                items_to_drop = api_endpoint(component_instance, user=user, *args, **kwargs) or []
                            for item_id in items_to_drop:
                                del self.context[item_id]
                            return items_to_drop

                        case MethodType.CREATE:
                            # Probably creating a new _story_ for a user:
                            # - requires a _user_ to own the story
                            # - passes the user argument through
                            # - the user will be linked in the created story, so it should be _unlinked_
                            #   before writing it into the context
                            # - the user's story list will have been updated, so we need to write-back the user
                            with self.open_user(user_id,
                                                write_back=True,
                                                acl=api_endpoint.access_level) as user:
                                # call the endpoint func to get a new context object and stash it
                                new_obj = api_endpoint(component_instance, user=user, *args, **kwargs)
                                if hasattr(new_obj, "user"):
                                    # If we got a story back, unlink the user before stashing it
                                    new_obj.user = new_obj.user.uid
                                self.context[new_obj.uid] = new_obj
                                return new_obj.uid

                        case _:
                            raise ValueError(f"Unsupported method type for user method: {api_endpoint.method_type}")

                else:
                    # Some admin or system task that doesn't require a user arg, but the service manager
                    # requires a user for access control.
                    match api_endpoint.method_type:
                        case MethodType.READ | MethodType.UPDATE:
                            with self.open_user(user_id, acl=api_endpoint.access_level):
                                # call the func and return the result
                                return api_endpoint(component_instance, *args, **kwargs)

                        case MethodType.DELETE:
                            with self.open_user(user_id, acl=api_endpoint.access_level):
                                items_to_drop = api_endpoint(component_instance, *args, **kwargs) or []
                            for item_id in items_to_drop:
                                del self.context[item_id]
                            return items_to_drop

                        case MethodType.CREATE:
                            # Probably creating a new _user_ as an admin task:
                            # - requires an appropriately privileged _super user_
                            # - doesn't pass the user argument through
                            # - doesn't write back the calling user's account (do we need bookkeeping?)
                            with self.open_user(user_id, acl=api_endpoint.access_level):
                                # call the endpoint func to get a new context object and stash it
                                new_obj = api_endpoint(component_instance, *args, **kwargs)
                                self.context[new_obj.uid] = new_obj
                                return new_obj.uid

                        case _:
                            raise ValueError(f"Unsupported method type for acl-only method: {api_endpoint.method_type}")

            else:
                # it's a public call with no endpoint context dep
                return api_endpoint(component_instance, *args, **kwargs)

        # Store our endpoint on the wrapper
        wrapper._api_endpoint = api_endpoint

        return wrapper
