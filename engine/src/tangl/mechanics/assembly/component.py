from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from tangl.core import Entity

ConnectorPolarity = Literal["plug", "socket"]


class ComponentFacet(BaseModel):
    """Lightweight context-bound contribution carried by an assembly component."""

    channel: str
    facet_type: str
    payload: object | None = None
    source_id: str | None = None
    subject_id: str | None = None

    def matches(self, channel: str | None = None, facet_type: str | None = None) -> bool:
        """Return whether this facet matches the requested coordinate."""

        if channel is not None and self.channel != channel:
            return False
        if facet_type is not None and self.facet_type != facet_type:
            return False
        return True

    def with_provenance(
        self,
        *,
        source_id: str | None = None,
        subject_id: str | None = None,
    ) -> "ComponentFacet":
        """Return a derived copy with missing provenance filled in."""

        return self.model_copy(
            update={
                "source_id": self.source_id or source_id,
                "subject_id": self.subject_id or subject_id,
            }
        )


class Component(Entity):
    """Assembly component that carries facets."""

    facets: list[ComponentFacet] = Field(default_factory=list)

    def component_facets(
        self,
        *,
        channel: str | None = None,
        facet_type: str | None = None,
        subject_id: str | None = None,
    ) -> list[ComponentFacet]:
        """Return matching facets with derived source/subject provenance."""

        source_id = str(self.uid)
        return [
            facet.with_provenance(source_id=source_id, subject_id=subject_id)
            for facet in self.facets
            if facet.matches(channel=channel, facet_type=facet_type)
        ]


class Connector(Component):
    """Assembly component endpoint that can associate with a compatible endpoint."""

    connector_shape: str
    connector_polarity: ConnectorPolarity
