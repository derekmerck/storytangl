from typing import Optional, Any
from enum import Enum

import yaml
from pydantic import ConfigDict, Field

from tangl.core.entity import Node, Graph  # Must import graph to define Node subclasses


class JournalFragment(Node):
    # red, output, linked within by red, without by yellow
    """
    Represents a basic content element and the core schema for communicating
    content to the front-end.

    Renderables generate lists of journal fragments with themselves as the parent.
    The journal layer of the graph is made up of ordered content fragments generated
    by structure nodes as they are traversed by the graph cursor.

    GroupFragments and UpdateFragments are _control_ objects in the fragment stream.

    KvFragments, MediaFragments, and DiscourseFragments have special rules for how the
    content field is represented.

    Minimal content fragment, fundamental unit for trace processes journal/log
    output.  Extended elsewhere.

    Fragments may be connected to their originating structure or resource nodes
    by 'blame' edges if they are part of the same graph.

    Edges between journal items are implicit in sequence since the journal is strictly
    linear and monotonic in sequence.

    Attributes:
    - fragment_type: General type of fragment, i.e., text, media, kv, runtime, used
      for automatically inferring fragment type from data.
    - label (str): Optional name/key for the fragment
    - content (str): Optional value/text/media for the fragment
    - content_format: Instruction for how to parse content field, ie, markdown or encoded data
    """
    # fragments are immutable once created
    model_config = ConfigDict(frozen=True)

    fragment_type: Optional[str|Enum] = Field("content", alias='type')  # intent for content, e.g., 'text', 'choice', 'media'
    content: Any
    # seq and mime-type are added in the service layer, when the fragment is serialized into a dto.

    def __str__(self):
        data = self.model_dump()
        s = yaml.dump(data, default_flow_style=False)
        return s
