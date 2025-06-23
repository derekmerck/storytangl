# A frozen fragment of the collapsing graph projected onto 1-d journal-space

from typing import Optional, Any

from pydantic import Field, BaseModel, ConfigDict, model_validator
import yaml

import tangl.utils.setup_yaml
from tangl.type_hints import Identifier
from tangl.core.solver.journal import JournalFragment
from .presentation_hints import PresentationHints

class ContentFragment(JournalFragment, extra='allow'):
    """
    Represents a basic content element and the core schema for communicating
    story- and info-content to the front-end.

    Renderables generate lists of content fragments with themselves as the parent.
    The journal layer of the graph is made up of ordered content fragments generated
    by structure nodes as they are traversed by the graph cursor.

    GroupFragments and UpdateFragments are _control_ objects in the fragment stream.

    KvFragments, MediaFragments, and TextFragments have special rules for how the
    content field is represented.

    Content in a KvFragment is a single key value pair along with styling information.
    Kv fragments almost always come in KvList groups, which can be interpreted as an
    ordered, styled dictionary.

    Presentation hint fields are optional and may not be respected by the client.

    Attributes:
    - fragment_type: General type of fragment, i.e., text, media, kv, runtime, used
      for automatically inferring fragment type from data.
    - label (str): Optional name/key for the fragment
    - content (str): Optional value/text/media for the fragment
    - content_format: Instruction for how to parse content field, ie, markdown or encoded data
    """
    # base features
    presentation_hints: Optional[PresentationHints] = Field(None, alias='hints')

    # If the fragment belongs to a group of fragments, declare the master's fragment_id
    group_id: Optional[Identifier] = None
    group_role: Optional[str] = None

    # If not wrapped in a response, can be used with batches to assemble a response on client end
    response_id: Optional[Identifier] = None
    sequence: Optional[int] = None

    # Indicate if fragment can be "activated", for choices, allow the choice to be selected, etc.
    activatable: Optional[bool] = False
    # For activatable fragments, is this fragment _currently_ active.
    active: Optional[bool] = True
    # Params to be included with the cb if the fragment is "activated", ie, a choice, link, button, input, rollover hint, custom ui event trigger
    activation_payload: Optional[Any] = None

