from typing import Type

from fastapi import APIRouter

from tangl.service.api_endpoints import HasApiEndpoints

# We want to mangle the names a little
# - starts with "get_" -> a get request, drop the prefix, drop the group if it matches
# - starts with "drop_" -> a del request, drop the prefix, drop the group if it matches -> drop_user_story -> del user/story
# - starts with anything else -> a post request, drop the group if it matches, ie, create_user -> post user/create
# add tags for endpoint type
# need to wrap bare responses with response_type

class FastApiAdapter:
    """Creates FastAPI routes from ServiceManager"""

    @classmethod
    def create_router(cls, service_manager: HasApiEndpoints):
        router = APIRouter()

        for name, endpoint in service_manager.get_api_endpoints().items():
            # Create route with appropriate method
            router.add_api_route(
                f"/{name}",
                endpoint,
                methods=["POST"] if endpoint.metadata.mutates_state else ["GET"],
                response_model=endpoint.metadata.response_type
            )

        return router