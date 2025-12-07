import tangl.api as api
from tangl.api import UpdateResponse
from tangl.story import World

from controllers import _story_for_tok, _prep_response

#####################################
# Restricted/Dev
#####################################

def do_set_current_block( sc_: str, token_info,
                          bl_: str = "start" ) -> UpdateResponse:
    with _story_for_tok(token_info) as ctx:
        res_ = api.set_current_block( ctx, f"{sc_}/{bl_}" )
        res = _prep_response( res_ )
        return res

def do_inspect( uid: str, token_info ) -> dict:
    with _story_for_tok(token_info) as ctx:
        res = api.inspect(ctx, uid)
        return res

def do_eval( body, token_info ) -> str:
    with _story_for_tok(token_info) as ctx:
        expr = body.get( "expr" )
        return api.do_eval( ctx, expr )

def do_exec( body, token_info ) -> bool:
    with _story_for_tok(token_info) as ctx:
        expr = body.get( "expr" )
        return api.do_exec( ctx, expr )

# stateless, but restricted
def do_get_scene_directory( wo_: str ) -> dict:
    wo = World[wo_]  # type: World
    res_ = api.get_scene_directory( wo )
    res = _prep_response( res_ )
    return res

