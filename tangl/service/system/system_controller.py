from tangl.service.api_endpoints import HasApiEndpoints, ApiEndpoint, AccessLevel, MethodType
from .system_info import SystemInfo

class SystemController(HasApiEndpoints):

    @ApiEndpoint.annotate(access_level=AccessLevel.PUBLIC)
    def get_system_info(self, **kwargs) -> SystemInfo:
        ...

    @ApiEndpoint.annotate(access_level=AccessLevel.RESTRICTED, method_type=MethodType.UPDATE)
    def reset(self, hard: bool = False, **kwargs) -> SystemInfo:
        # This is just for the annotation, it is actually handled entirely
        # in the service manager.
        raise NotImplementedError
