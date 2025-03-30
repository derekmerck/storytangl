from tangl.service.api_endpoints import ServiceManager
from tangl.business.story.story_controller import StoryController
from tangl.business.world.world_controller import WorldController
from tangl.service.user.user_controller import UserController
from tangl.service.system.system_controller import SystemController

from tangl.rest.fastapi_adapter import FastApiAdapter

def main():
    # todo: context-type should be based on config
    context = dict()
    service_manager = ServiceManager(context=context,
                                     components=[SystemController,
                                                 WorldController,
                                                 UserController,
                                                 StoryController])
    app = FastApiAdapter(service_manager)
    # todo: add a media server and middleware to link rits to media urls
    app.run()


if __name__ == '__main__':
    main()
