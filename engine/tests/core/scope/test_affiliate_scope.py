from typing import Self
import logging

from tangl.core.entity import Entity
from tangl.core.scope import AffiliateScope, HasAffiliateScopes
from tangl.core.handlers import on_gather_context

logger = logging.getLogger(__name__)

class MyScope(AffiliateScope):

    @on_gather_context.register(caller_cls=Entity, domain=Self)
    def _log_request_from_caller(self, caller: Entity, **kwargs):
        msg = f"{self!r}.on_gather() invoked for {caller!r}"
        logger.debug(msg)

def test_affiliate_scope():
    entity = HasAffiliateScopes(locals={"foo": "bar"}, domains=[MyScope()])
    logger.debug( f"context: {entity.gather_context()}" )
    ctx = entity.gather_context()
    assert ctx["foo"] == "bar"
    assert 'self' in ctx
    assert 'tangl_version' in ctx

    # should trigger logging as well b/c of the affiliate handler ...
