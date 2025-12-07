
from controllers import _account_for_tok

def do_get_current_story( token_info ) -> str:
    with _account_for_tok( token_info) as account:
        return account.current_story.uid

def do_clear_story(wo_: str, token_info):
    with _account_for_tok(token_info) as account:
        del account.stories[wo_]
