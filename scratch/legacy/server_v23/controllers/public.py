import flask

import tangl.api as api
from tangl.story import World
from controllers import _prep_response


#####################################
# Stateless/Public
#####################################
def do_get_api_key( secret: str = None ) -> dict | flask.Response:
    """
    IMPORTANT!  Setting cookies requires samesite=None, secure=True
    if api is not on the same TLD or the game-specific images
    (i.e., avatars) won't show up
    """
    api_key, secret = api.get_api_key(secret)
    res = {"secret": secret,
           "api_key": api_key}

    # Using cookies is a bit of a hassle now that browsers default to rejecting them,
    # so we dropped this for now.
    try:
        import flask
        r = flask.make_response(res)
        r.set_cookie("X-Auth", api_key)
        return r
    except RuntimeError:
        # No flask context, probably testing
        print( "Warning, unable to set x-auth cookie")
        return res

# -----------------------------------
# World-specific
# ------------------------------------
def do_get_world_info( wo_: str ) -> dict:
    wo = World[wo_]  # type: World
    res_ = api.get_world_info( wo )
    res = _prep_response( res_ )
    return res

def do_get_world_image( wo_: str, grp_: str, im_: str ) -> str:
    wo = World[wo_]  # type: World
    return api.get_world_image( wo, f"{grp_}/{im_}", format="svg" )
