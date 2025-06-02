import logging

import humanize

from tangl.info import __version__, __title__, __url__
from tangl.utils.app_uptime import app_uptime
# todo: Be sure to import app uptime on startup so the clock starts running
from tangl.service.api_endpoint import HasApiEndpoints, ApiEndpoint, AccessLevel, MethodType, ResponseType
from .system_info import SystemInfo

logger = logging.getLogger(__name__)

class SystemController(HasApiEndpoints):
    """
    Provides basic methods for interacting with the underlying service.

    public api:
      - get_system_info

    dev api:
      - reset
    """

    ###########################################################################
    # System Public API
    ###########################################################################

    @ApiEndpoint.annotate(access_level=AccessLevel.PUBLIC)
    @staticmethod
    def get_system_info(self, **kwargs) -> SystemInfo:
        try:
            from tangl.world import World
            num_worlds = len(World._instances)
        except ImportError:
            num_worlds = 0

        info = SystemInfo(
            engine=__title__,
            version=__version__,
            uptime=humanize.naturaldelta(app_uptime()),
            homepage_url=__url__,
            worlds=num_worlds,
            users=1
        )
        # "media": [ MediaNode(media_role="info_im", **__info_image__) ],
        # server will inject api url and guide url

        logger.debug(info)
        return info

    ###########################################################################
    # System Dev API
    ###########################################################################

    @ApiEndpoint.annotate(access_level=AccessLevel.RESTRICTED,
                          method_type=MethodType.UPDATE,
                          response_type=ResponseType.RUNTIME)
    @staticmethod
    def reset_system(hard: bool = False):
        """
        Reload all worlds.

        Passing the "hard" parameter resets persistence as well.
        """
        # This is just for the annotation, it is actually handled entirely
        # in the service manager.
        raise NotImplementedError
