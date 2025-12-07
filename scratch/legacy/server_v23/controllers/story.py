import tangl.api as api
from tangl.utils.type_vars import StoryUpdate

from controllers import _story_for_tok, _prep_response


def do_get_current_block( token_info ) -> StoryUpdate:
    with _story_for_tok(token_info) as ctx:
        res_ = api.get_current_block( ctx )
        res = _prep_response( res_ )
        return res

def do_do_action( uid: str, body, token_info ) -> StoryUpdate:
    with _story_for_tok(token_info) as ctx:
        body = body or {}
        res_ = api.do_action( ctx, uid, **body )
        res = _prep_response( res_ )
        return res

# Non mutating, but lock so it is not updated during req
def do_get_status(token_info) -> StoryUpdate:
    with _story_for_tok(token_info) as ctx:
        res_ = api.get_status(ctx)
        res = _prep_response(res_)
        return res

def do_get_story_image(uid: str, token_info) -> str:
    with _story_for_tok(token_info) as ctx:
        res = api.get_story_image(ctx, uid, format="svg")
        return res
