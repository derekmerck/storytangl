# This uses a control-display-interact loop similar to the one in tangl cli

init python:

    config.default_transform = Transform( style="bottom" )
    config.layers.insert( config.layers.index( "master" ), "background" )

    import importlib
    from uuid import UUID
    import tempfile
    from tangl.config import settings
    from tangl.service import ServiceManager

    world_id = settings.client.default_world
    importlib.import_module(world_id)

    sm = ServiceManager()

    def get_user_credentials(secret: str, world_id: str) -> UUID:
        response = sm.create_user(secret)
        user_id = response.user_id
        response = sm.create_story(user_id, world_id)
        service_manager.set_current_story_id(user_id, world_id)
        return user_id

    user_id = get_user_credentials(settings.client.secret, world_id, sm)

    def client_update():

        current = sm.get_story_update( user_id )

        def render_block( blk ):
            narrator(blk['text'], interact=False)
            # if 'images' in blk:
            #     renpy.scene( blk['images'][0] )
            if 'actions' in blk:
                actions_ = []
                for ac in blk['actions']:
                    actions_.append( (ac['text'], ac['uid']) )
                result = renpy.display_menu( actions_ )
                sm.do_action( user_id, result )
                renpy.jump("block")

        for blk in current:
            render_block( blk )

# The game starts here.

label start:

    image bgImg = Frame( Solid( "#140e0e" ), size=( config.screen_width, config.screen_height ) )
    show bgImg onlayer background
    # image sc_im = im.Scale( "scene_im.png", config.screen_height, config.screen_height )
    image sc_im = Image( "scene_im.png" )
    scene sc_im

    jump block

label block:

    $ client_update()

label done:

    e "You've created a new Ren'Py game.  I'm a dog!"

    e "Once you add a story, pictures, and music, you can release it to the world!"

    return

label west:

    e "I see that you have gone west!"

    return
