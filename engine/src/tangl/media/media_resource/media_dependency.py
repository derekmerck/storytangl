from pathlib import Path
from typing import Any, ClassVar

from pydantic import ConfigDict, model_validator, Field

from tangl.type_hints import Identifier
from tangl.vm import Dependency, ProvisionPolicy, Requirement
from tangl.media.type_hints import Media
from tangl.media.media_creators.media_spec import MediaSpec
from .media_resource_inv_tag import MediaRITStatus, MediaResourceInventoryTag as MediaRIT

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
    def _pre_resolve(cls, data: Any):
        if not isinstance(data, dict) or "requirement" in data:
            return data

        payload = dict(data)
        identifier = payload.get("media_id")
        media_path = payload.get("media_path")
        media_scope = payload.get("scope")
        media_data = payload.get("media_data")
        media_spec = payload.get("media_spec")
        explicit_policy = "provision_policy" in payload or "policy" in payload
        hard = bool(payload.pop("hard_requirement", payload.pop("hard", False)))
        default_policy = ProvisionPolicy.ANY if media_spec is not None else ProvisionPolicy.EXISTING
        policy_value = payload.pop("provision_policy", payload.pop("policy", default_policy))

        requirement_kwargs: dict[str, Any] = {
            "has_kind": MediaRIT,
            "provision_policy": policy_value,
            "hard_requirement": hard,
        }

        if identifier:
            requirement_kwargs["has_identifier"] = identifier
            requirement_kwargs["authored_path"] = str(identifier)
        elif media_path:
            media_path_obj = Path(media_path)
            requirement_kwargs["has_identifier"] = media_path_obj.name
            requirement_kwargs["path"] = media_path_obj
            requirement_kwargs["authored_path"] = str(media_path)

        if media_scope:
            requirement_kwargs["has_tags"] = {f"scope:{media_scope}"}

        if media_data is not None:
            requirement_kwargs["fallback_templ"] = MediaRIT(
                data=media_data,
                data_type=payload.get("data_type"),
            )

        if media_spec is not None:
            if not isinstance(media_spec, MediaSpec):
                media_spec = MediaSpec.from_authoring(media_spec)
                payload["media_spec"] = media_spec
            requirement_kwargs["media_spec"] = media_spec
            requirement_kwargs["media_ref_id"] = payload.get("predecessor_id")
            requirement_kwargs["media_basename"] = payload.get("label") or payload.get("media_role") or "media"
            if not explicit_policy:
                requirement_kwargs["provision_policy"] = ProvisionPolicy.ANY
            payload.setdefault("realized_spec", None)
            payload.setdefault("final_spec", None)
            payload.setdefault("script_spec", media_spec.normalized_spec_payload())

        payload["requirement"] = Requirement(**requirement_kwargs)
        return payload

    media_id: Identifier | None = Field(default=None, init_var=True)
    media_path: str | None = Field(default=None, init_var=True)
    media_data: Media | None = Field(default=None, init_var=True)
    media_spec: MediaSpec | None = Field(default=None, init_var=True)
    media_role: str | None = None
    caption: str | None = None
    scope: str | None = None
    script_spec: dict[str, Any] | None = None
    realized_spec: dict[str, Any] | None = None
    final_spec: dict[str, Any] | None = None

    @property
    def render_ready(self) -> bool:
        """Return ``True`` when the dependency is satisfied by a resolved provider."""
        if not self.satisfied:
            return False
        return (
            self.provider is not None
            and getattr(self.provider, "status", MediaRITStatus.RESOLVED) == MediaRITStatus.RESOLVED
        )
