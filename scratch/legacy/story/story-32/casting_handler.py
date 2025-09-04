from __future__ import annotations
import random
from typing import Optional, ClassVar, Self
import logging
from uuid import UUID

from pydantic import model_validator, Field

from tangl.type_hints import UniqueLabel, StringMap, Strings, Tags
from tangl.core.handler import BaseHandler
from tangl.core.graph.handlers import AssociationHandler
from tangl.story import Story, StoryLink
from tangl.story.asset import Asset, Fungible, Wallet
from .actor import Actor

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)

class CastingHandler(BaseHandler):
    from pydantic import BaseModel
    from typing import Optional, Dict, Any

    @classmethod
    def cast_by_cloning(cls, story: Story, casting_ref, casting_template) -> Optional[Actor]:
        actor = story.get_node(casting_ref)
        if not actor:
            return None
        new_actor = actor.model_copy(update=casting_template)
        # Ensure we call init and register it
        story.add_node(new_actor)
        return new_actor

        @classmethod
        def _cast_replica(cls, self) -> Optional[Actor]:
            """Biologically similar"""
            prime = self._cast_ref()
            if prime is None:
                return None

            if hasattr(prime, "as_body_kwargs"):
                kwargs = prime.as_body_kwargs()
            else:
                kwargs = prime.model_dump(exclude={'name', 'surname', 'meta', 'parent'})

            kwargs.update(self.template)

            if self.locals.get("preserve_surname"):
                kwargs['surname'] = prime.surname

            obj = Actor(**kwargs, parent=self)
            if self.world:
                self.world.init_node(obj)  # will call world init, if any
            else:
                obj.__init_entity__()

            # Handle replicas
            if "replicas" not in prime.locals:
                prime.locals['replicas'] = set()
            prime.locals['replicas'].add(obj.uid)
            obj.locals['replicas'] = prime.locals['replicas']  # ref will share future updates

            return obj



    @classmethod
    def cast_by_cloning(cls, story: Story, casting_ref, casting_template) -> Optional[Actor]:
        actor = story.get_node(casting_ref)
        if not actor:
            return
        new_actor = actor.evolve( **casting_template )
        # todo: ensure we call init and register it
        return new_actor

    @classmethod
    def _cast_replica(cls, self) -> Actor | None:
        """Biologically similar"""
        prime = self._cast_ref()
        if prime is None:
            return
        if hasattr( prime, "as_body_kwargs"):
            kwargs = prime.as_body_kwargs()
        else:
            kwargs = prime.asdict()
            for field in ['name', 'surname', 'meta', 'parent']:
                if field in kwargs:
                    kwargs.pop( field )

        kwargs |= self.template

        if "preserve_surname" in self.locals:
            kwargs['surname'] = prime.surname

        obj = Actor( **kwargs, context=self.context, parent=self )
        if self.world:
            self.world.init_node(obj)   # will call world init, if any
        else:
            obj.__init_entity__()

        # todo: cheating for now and using eid instead of a real ref
        if "replicas" in prime.locals:
            prime.locals['replicas'].add( obj.pid )
        else:
            prime.locals['replicas'] = { prime.pid, obj.pid }
        obj.locals['replicas'] = prime.locals['replicas']  # ref will share future updates

        return obj



