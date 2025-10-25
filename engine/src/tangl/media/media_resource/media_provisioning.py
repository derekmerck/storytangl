from typing import Optional
from dataclasses import dataclass, field

from tangl.type_hints import StringMap, Identifier, UnstructuredData
from tangl.core import Node, BehaviorRegistry
from tangl.vm.planning import Provisioner
from tangl.media.type_hints import Media
from tangl.media.media_creators.media_spec import MediaSpec
from .media_resource_inv_tag import MediaResourceInventoryTag as MediaRIT
from .media_resource_registry import MediaResourceRegistry

on_provision_media = BehaviorRegistry(label="provision_media")

@dataclass
class MediaProvisioner(Provisioner):
    # Discover or create RIT for a media requirement

    # Existing is unchanged, no need to override
    # def _resolve_existing(*args, **kwargs): ...

    def _resolve_update(*args, **kwargs):
        raise NotImplementedError("Media UPDATE not implemented")

    def _resolve_clone(*args, **kwargs):
        raise NotImplementedError("Media CLONE not implemented")

    def _resolve_create(self, provider_template: UnstructuredData) -> MediaRIT:
        """Create RIT from data or spec"""
        if 'data' in provider_template:
            data = provider_template['data']  # type: Media
            provider = MediaRIT(data=data)
        elif 'spec' in provider_template:
            spec = provider_template['spec']  # type: MediaSpec
            # todo: this should be async, schedule it,
            #       how do we pass reference node for adapter stage?
            adapted_spec = spec.adapt_spec(self.requirement.reference)
            # todo: try to discover a rit for the adapted spec now
            media, revised_spec = adapted_spec.create_media()
            provider = MediaRIT(spec=adapted_spec, data=media, final_spec=revised_spec)
        else:
            raise ValueError("Media CREATE requires either data or spec")

        self.registries[0].add(provider)
        return provider
