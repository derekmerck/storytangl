from typing import Dict, Any, Optional
from uuid import UUID
from datetime import datetime

from pydantic import BaseModel, Field
from fastapi import FastAPI, APIRouter, Depends, Header, Body, Query, HTTPException

from tangl.service.api_endpoints import ServiceManager, ApiEndpoint, MethodType, ResponseType, AccessLevel
# todo: wrap ContentResponse types in the ContentResponse model.
from .content_response import ContentResponse

class RuntimeResponse(BaseModel):
    """
    Example minimal response for non-GET calls.
    Provides metadata about the call, the user, the arguments, and the final result.
    """
    called_by: Optional[UUID] = None
    endpoint: str
    args: Dict[str, Any]
    result: Any
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())

class FastApiAdapter:
    """
    Creates FastAPI routes from a ServiceManager.

    The adapter inspects each endpoint and:
      - Deduces the HTTP method from the endpoint's MethodType or name prefix
      - Creates an APIRouter per group (like 'story', 'user')
      - Injects user_id from header if needed (access_level>PUBLIC)
      - Mangles route paths to drop group/prefix from the function name.
    """

    def __init__(self, service_manager: ServiceManager):
        self.service_manager = service_manager
        # dictionary of group_name -> APIRouter
        self.routers = {}

    def create_app(self, title="My API", version="1.0"):
        """
        Creates a FastAPI app, includes each group router with prefix=/{group}.
        """
        app = FastAPI(title=title, version=version)
        # For each endpoint in service_manager.endpoints, build or retrieve a router
        self._build_routers()
        # Now add them to the app
        for group_name, router in self.routers.items():
            prefix = f"/{group_name}" if group_name else ""
            app.include_router(router, prefix=prefix)
        return app

    def _build_routers(self):
        """
        Iterate over service_manager.endpoints, parse the group,
        pick an HTTP method, define the route path, attach a route function to the appropriate APIRouter.
        """
        for endpoint_name, endpoint_callable in self.service_manager.endpoints.items():
            api_endpoint = endpoint_callable._api_endpoint  # the ApiEndpoint instance
            group = api_endpoint.group or ""  # fallback if no group
            router = self.routers.setdefault(group, APIRouter(tags=[group.capitalize() or "Misc"]))

            http_verb = api_endpoint.method_type.http_verb()

            # Build the route path from the function name
            route_path = self._mangle_name_to_path(api_endpoint)

            # Decide on a response_model
            if http_verb == "GET":
                # We might interpret the endpoint's response_type to decide a pydantic model
                # For demonstration, let's skip or do a simple or None
                response_model = None
            else:
                # For non-GET, we wrap everything in a generic RuntimeResponse
                response_model = RuntimeResponse

            # Build the actual route function
            route_func = self._make_route_func(api_endpoint, response_model)
            # attach it
            router.add_api_route(
                route_path,
                route_func,
                methods=[http_verb],
                response_model=response_model,
                # optionally set status_code, etc.
            )

    def _mangle_name_to_path(self, api_endpoint: ApiEndpoint) -> str:
        """
        Convert 'get_story_info' to '/info', dropping the prefix
        that indicates the method or the group name.
        e.g., 'drop_user_thing' -> '/thing'
        """
        name = api_endpoint.name

        # If the function name starts with get_/create_/drop_/update_ etc., remove it
        for prefix in ("get_", "create_", "drop_", "update_", "do_"):
            if name.startswith(prefix):
                name = name[len(prefix):]
                break

        # If the function name starts with the group, remove it
        group = api_endpoint.group or ""
        if group and name.startswith(group + "_"):
            name = name[len(group) + 1:]

        # convert underscores to slashes or just keep underscores
        # example: "user_story_info" => "/story_info" or "/story/info"
        # up to you:
        route_path = "/" + name.replace("_", "/")
        return route_path

    def _make_route_func(self, api_endpoint: ApiEndpoint, response_model):
        """
        Create the actual function that FastAPI calls.
        We'll parse user_id from a header if needed, etc.
        """
        # The underlying function that the manager calls is self.service_manager.endpoints[...]
        endpoint_key = self._find_endpoint_key(api_endpoint)
        # the bound function we call in the manager
        manager_func = self.service_manager.endpoints[endpoint_key]

        async def route_func(
            # If the endpoint requires a user, parse from header:
            x_auth: Optional[str] = Header(None, alias="x-auth"),
            # we can parse query/body as well if needed...
            **extra_kwargs
        ):
            # if access_level>PUBLIC, we require x_auth
            if api_endpoint.access_level > AccessLevel.PUBLIC:
                if not x_auth:
                    raise HTTPException(status_code=401, detail="User authentication required.")
                # decode x_auth => user_id
                user_id = self._decode_user_id(x_auth)
                extra_kwargs["user_id"] = user_id

            # Now call the manager function
            # If it's a GET, might just return manager_func(...)
            result = manager_func(**extra_kwargs)

            # If we have a non-GET => wrap in runtime model
            if response_model is RuntimeResponse:
                return RuntimeResponse(
                    called_by=extra_kwargs.get("user_id"),
                    endpoint=api_endpoint.name,
                    args=extra_kwargs,
                    result=result,
                )
            else:
                return result

        return route_func

    def _find_endpoint_key(self, api_endpoint: ApiEndpoint) -> str:
        """
        Reverse-lookup in self.service_manager.endpoints to find the key
        that references this particular ApiEndpoint object.
        """
        for k, v in self.service_manager.endpoints.items():
            # v._api_endpoint is the same object as api_endpoint
            if getattr(v, "_api_endpoint", None) == api_endpoint:
                return k
        raise ValueError(f"Could not find manager endpoint key for {api_endpoint.name}")

    def _decode_user_id(self, x_auth_value: str) -> UUID:
        """
        Example placeholder for mapping an auth header to a user UUID.
        You can do real logic, e.g. decode a token or do a db lookup.
        """
        # For demonstration, assume x_auth_value is just a UUID string
        return UUID(x_auth_value)
