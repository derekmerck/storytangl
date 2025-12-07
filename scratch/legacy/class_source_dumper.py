"""
Generate a unified document that includes all super-classes and handlers
for a given group of classes.
"""

import importlib
from typing import Type
from pprint import pprint
from pathlib import Path

from tangl.entity import *
from tangl.entity.smart_new import *
from tangl.entity.mixins import *
from tangl.graph import *
from tangl.graph.mixins import *
from tangl.graph.mixins.connection import Connection

from tangl.story.story import StoryNode, Story
from tangl.story.journal_models import *
from tangl.story.scene import *
from tangl.story.actor import *

from tangl.journal import Journal
from tangl.world import World

from tangl.service import ServiceManager
from tangl.utils.inheritance_aware import InheritanceAware

core_entity = {Entity, Templated, Renderable, Lockable, HasEffects, HasNamespace, Conditional, InheritingSingleton, SingletonEntity, NamespaceHandler, RenderHandler, ConditionHandler, EffectHandler, AvailabilityHandler, SmartNewHandler}

core_node = {UsesPlugins, Associating, HasCascadingNamespace, TraversableNode, Node, AssociationHandler, TraversalHandler, Edge, WrappedSingleton, Graph, TraversableGraph}

core_story = {StoryNode, Story}

outfile = "dumps/world_src.py"

class CandidateClass(World):
    ...

res = CandidateClass.get_all_superclass_source(
    ignore=[CandidateClass, InheritanceAware, *core_entity, *core_node, *core_story],
    docs_only=[],
    include_base_entity_handler=False,
    as_yaml=False,
)

res_sorted = sorted( res.items(), key=lambda k: k[0][3:] if k[0].startswith("Has") else k[0])
res = "\n---\n".join([v[1] for v in res_sorted])

print( res )

def dump(outfile):
    with open(outfile, 'w') as f:
        f.writelines( res )

if outfile:
    dump(outfile)
