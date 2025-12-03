
from tangl.world.world import World
from tangl.story import Story
from tangl.account import Account

from tests.conftest import TEST_WORLD_PATH

import pytest


def test_super_ctx( wo ):

    sctx = SuperContext()
    ctx = sctx.get_ctx( wo.uid )

    assert( "main_menu" in ctx )
    assert( "main_menu/start" in ctx )
    assert( "main_menu/start/ac0" in ctx )
    assert( ctx['main_menu/start/ac0'].context == ctx )

    assert( wo.uid in ctx.ns() )
    print( ctx.ns()[wo.uid] )
    print( ctx.ns()[wo.uid].achievements )

    world2 = World(uid="world2",
                   entry="main_menu",
                   cls_template_maps={'Scene':
                                      {'main_menu':
                                           {'uid': 'main_menu'}}})

    print( world2 )

    with sctx( "world2" ) as ctx:
        print( ctx.world.uid )
        print( ctx.ns()['sample'] )
        print( ctx.ns()['world2'] )


def test_super_ctx_manager( wo ):

    sctx = SuperContext()
    ctx = sctx.get_ctx( wo.uid )
    ctx_mgr = SimpleSctxManager()

    with ctx_mgr( "my_client", "sample" ) as ctx:
        assert ctx.world.uid == "sample"
        print( ctx.ns()['sample'] )

    with ctx_mgr( "my_client" ) as ctx:
        assert ctx.world.uid == "sample"
        print( ctx.ns()['sample'] )

    world2 = World(uid="world2",
                   entry="main_menu",
                   cls_template_maps={'Scene':
                                      {'main_menu':
                                           {'uid': 'main_menu'}}})

    print( world2 )

    with ctx_mgr( "my_client", "world2" ) as ctx:
        assert ctx.world.uid == "world2"
        print( ctx.ns()['world2'] )
        print( ctx.ns()['sample'] )

