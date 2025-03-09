from tangl.service.api_endpoints import ServiceManager
from tangl.business.story.story_controller import StoryController, ContentFragment
from tangl.business.world.world_controller import WorldController, WorldInfo
from tangl.service.user.user_controller import UserController, UserInfo
from tangl.service.system.system_controller import SystemController, SystemInfo
from .fastapi_adapter import FastApiAdapter

def main():
    context = dict()
    service_manager = ServiceManager(context=context,
                                     components=[SystemController,
                                                 WorldController,
                                                 UserController,
                                                 StoryController])
    app = FastApiAdapter(service_manager)
    app.run()


if __name__ == '__main__':
    main()
