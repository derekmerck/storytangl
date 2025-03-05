from tangl.service.api_endpoints import HasApiEndpoints, ApiEndpoint, AccessLevel, MethodType
from .system_info import SystemInfo

class SystemController(HasApiEndpoints):

    @ApiEndpoint.annotate(access_level=AccessLevel.PUBLIC)
    def get_system_info(self, **kwargs) -> SystemInfo:
        ...
