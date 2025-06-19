import logging
from typing import Self
from collections import ChainMap

from pydantic import Field

from tangl.info import __version__
from tangl.type_hints import StringMap
from tangl.core.entity import Entity, Graph
from tangl.core.dispatch import HasHandlers, HandlerPriority as Priority
from tangl.core.handler import HasContext, on_gather_context

logger = logging.getLogger(__name__)

class AffiliateScope(HasContext, HasHandlers):
    """
    Affiliate scopes are just collections of affiliated entities with some
    shared context.  It is strictly opt-in, the scope itself doesn't track
    its members.

    Because it inherits from "HasContext", it will provide its locals when
    _asked explicitly_ for them.  For example, when including a gather handler
    that delegates to an affiliated scope.

    If you want to _always inject_ a handler into an affiliate's pipeline, use
    an instance handler that invokes on Entities that match criteria `domain=Self`.
    However, be careful with this as it could leak and pollute other pipelines if
    the match criteria is too broad.
    """

global_domain = AffiliateScope(label="global_domain")

@on_gather_context.register(caller_cls=Entity, bind_to=global_domain)
def inject_version_info(self, caller: Entity, **kwargs):
    return {"tangl_version": __version__}


class HasAffiliateScopes(HasContext):

    domains: list[AffiliateScope] = Field(default_factory=list)

    def has_domain(self, domain: AffiliateScope) -> bool:
        return domain in self.domains

    @on_gather_context.register(priority=Priority.EARLY)
    def _addend_domain_context(self: Graph, **kwargs) -> StringMap:
        # To avoid gathering domain info redundantly, we will only call it once,
        # and include it in the graph's context.  In turn, nodes call for their
        # graph's context only once.
        if len(self.domains) == 0:
            return None
        elif len(self.domains) == 1:
            return self.domains[0].gather_context()
        else:
            maps = [ d.gather_context() for d in self.domains ]
            return ChainMap( *maps )


class MyScope(AffiliateScope):

    @on_gather_context.register(caller_cls=Entity, domain=Self)
    def _log_request_from_caller(self, caller: Entity, **kwargs):
        msg = f"{self!r}.on_gather() invoked for {caller!r}"
        logger.debug(msg)


logging.basicConfig(level=logging.DEBUG)

def test_affiliate_scope():
    entity = HasAffiliateScopes(locals={"foo": "bar"}, domain=MyScope())
    logger.debug( f"context: {entity.gather_context()}" )
    ctx = entity.gather_context()
    assert ctx["foo"] == "bar"
    assert 'self' in ctx
    assert 'tangl_version' in ctx

    # should trigger logging as well b/c of the affiliate handler ...
