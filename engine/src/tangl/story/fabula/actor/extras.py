from pydantic import Field

from tangl.type_hints import StringMap
from .role import Role
from .actor import Actor


class Extras(Role):
    """
    Extra is an extension of role that can generate batches of random generic actors according
    to a template.
    """

    # _Required_
    successor_template: StringMap = Field(..., alias='actor_template')

    # todo: some extension to reuse generics that were generated previously?  Eventually a generic that appears several times becomes a permanent-generic

    def cast(self, n: int = 3) -> list[Actor]:
        result = []
        for i in range(n):
            extra = super().cast()
            extra.tags.add('generic')
            result.append(extra)
        return result

    def uncast(self):
        raise RuntimeError("Cannot uncast extras, just discard them from the graph.")

    def associate_with(self, actor: Actor, **kwargs):
        # No need to associate or disassociate with extras roles?
        pass
