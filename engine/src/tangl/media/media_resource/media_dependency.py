from typing import ClassVar

from pydantic import ConfigDict, model_validator, Field

from tangl.type_hints import Identifier
from tangl.vm.provision import Dependency, Requirement
from tangl.vm.provision.requirement import ProvisioningPolicy
from tangl.media.type_hints import Media
from tangl.media.media_creators.media_spec import MediaSpec
from .media_resource_inv_tag import MediaResourceInventoryTag as MediaRIT

# todo: probably want a media requirement subclass, then use that in a dependency and affordance subclass, media affordances are pre-decided media objects that can be attached as appropriate, first time you see a char etc.

class MediaDep(Dependency[MediaRIT]):
    """
    Links a graph node to a media resource.

    - story media script w path/url, media registry alias, or spec
    - story media dep is provisioned:
      - **path** rit is discovered or created directly from the path/url and linked
      - **registry alias** is validated linked
      - **spec** is transformed using an appropriate adapter for the parent node (actor, block, etc.) and its aliases are searched in the registry
        - if the spec alias is already in the media registry: link it
        - otherwise:
          - invoke the creator pipeline
          - the spec may also be updated creator-side with seed info or other random processes, so creators return a _realized_ spec and associated media data
          - register the returned media and update the node spec if the node is unrepeatable, otherwise leave it as the template so it can be re-rendered when the context is updated
          - link the new rit
    """
    model_config: ClassVar[ConfigDict] = ConfigDict(arbitrary_types_allowed=True)

    @model_validator(mode="before")
    @classmethod
    def _pre_resolve(cls, data):
        # Does the linked rit resolve the type?
        req_kwargs = {}
        if "media_id" in data:
            req_kwargs["identifier"] = data.pop("media_id")
        if "media_path" in data:
            req_kwargs["criteria"] = {'path': data.pop("media_path")}
        if "media_data" in data:
            # embedded data
            req_kwargs["template"] = {'data': data.pop("media_data")}
        if "media_spec" in data:
            # create on demand
            req_kwargs["template"] = {'spec': data.pop("media_spec")}

        requirement = Requirement.model_construct(
            graph=data.get("graph"),
            policy=req_kwargs.get("policy", ProvisioningPolicy.ANY),
            identifier=req_kwargs.get("identifier"),
            criteria=req_kwargs.get("criteria"),
            template=req_kwargs.get("template"),
        )
        data['requirement'] = requirement
        return data

    media_id: Identifier | None = Field(default=None, init_var=True)
    media_path: str | None = Field(default=None, init_var=True)
    media_data: Media | None = Field(default=None, init_var=True)
    media_spec: MediaSpec | None = Field(default=None, init_var=True)
