"""
Wraps api controllers for connexion
"""
from __future__ import annotations

from tangl.rest.locking import Lock
from contextlib import contextmanager
from typing import *

from tangl.account import Account, SimpleAccountMgr
from tangl.story import Story

# import redis_lock

# from tangl.utils.deep_md import deep_md
locking = False
deep_md = lambda x: x

# Simple ephemeral account manager
account_mgr = SimpleAccountMgr()

def check_api_key(api_key, required_scopes):
    # adds "token_info" to call args
    return {'api_key': api_key}

def _prep_response( res_: Union[List, Dict] ) -> Union[List, Dict]:
    res = deep_md( res_ )
    return res

def _get_key( token_info ):
    return token_info['api_key']

@contextmanager
def _account_for_tok( token_info ) -> Account:
    api_key = _get_key(token_info)
    with Lock(api_key):
        yield SimpleAccountMgr(api_key)

@contextmanager
def _story_for_tok( token_info ) -> Story:
    api_key = _get_key(token_info)
    with Lock(api_key):
        yield SimpleAccountMgr(api_key).current_story
