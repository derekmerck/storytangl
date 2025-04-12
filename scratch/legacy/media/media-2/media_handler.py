from uuid import UUID

from tangl.graph import Node
from tangl.resource_registry.resource_inventory_tag import ResourceInventoryTag as RIT
from .type_hints import MediaResource
from .media_spec import MediaSpecification
from .journal_model import JournalMediaItem
from .protocols import ResourceRegistryProtocol, MediaForgeProtocol
from .media_node import MediaNode

# todo: invoke on_prepare_media plugin

class MediaHandler:

    # --------------
    # Resource Generator Funcs
    # --------------

    @classmethod
    def _resource_from_external(cls, node: MediaNode):
        return JournalMediaItem(
            uid=node.uid,
            media_role=node.media_role,
            url=node.url)

    @classmethod
    def _resource_from_data(cls, node: MediaNode):
        return JournalMediaItem(
            uid=node.uid,
            media_role=node.media_role,
            data=node.data)

    @classmethod
    def _resource_from_rit(cls, node: MediaNode):
        return JournalMediaItem(
            uid=node.uid,
            media_role=node.media_role,
            _rit=node._rit)

    # --------------
    # Media Registry Handlers
    # --------------

    @classmethod
    def _get_registry_for(cls, node: MediaNode, **kwargs) -> ResourceRegistryProtocol:
        try:
            return node.graph.media_registry  # type: ResourceRegistryProtocol
        except:
            raise RuntimeError(f"Unable to infer appropriate media registry for {node}")
        # todo: other methods for finding appropriate registry ...

    @classmethod
    def _get_node_aliases(cls, node: MediaNode) -> list[UUID | str]:
        aliases = [ node.uid, node.name ]
        if node.final_spec:
            aliases.append( node.final_spec.uid )
        return aliases

    @classmethod
    def _rit_from_alias(cls, node: MediaNode) -> RIT:
        media_registry = cls._get_registry_for(node)
        rit = media_registry.find_resource( *cls._get_node_aliases(node) )
        if rit:
            node.rit = rit
            return rit
        else:
            raise KeyError(f"No resource found for {node.name}")

    @classmethod
    def _add_media_to_registry(cls, node: MediaNode, media: MediaResource) -> RIT:
        media_registry = cls._get_registry_for( node )
        return media_registry.add_resource( media, name=cls._get_node_aliases(node) )

    # --------------
    # check registry
    # --------------

    @classmethod
    def _rit_from_spec(cls, node: MediaNode,
                            spec_overrides: dict = None,
                            forge_kwargs: dict = None) -> RIT:
        if node.parent or spec_overrides:
            # Try to update the spec based on the parent node or passed kwargs
            spec_overrides = spec_overrides or {}
            node.realized_spec = node.media_spec.realize(node=node.parent, **spec_overrides)
            if node.realized_spec != node.spec:
                # check again for the realized spec
                if x := cls._rit_from_alias(node):
                    # found it
                    return x, None
        else:
            node.realized_spec = node.spec

        media, node.final_spec = cls._create_media(node.realized_spec, **forge_kwargs)
        node._rit = cls._add_media_to_registry(node, media)
        return node._rit

    @classmethod
    def _create_media(cls, media_spec: MediaSpecification, **forge_kwargs) -> tuple[MediaResource, MediaSpecification]:
        forge = media_spec.get_forge(**forge_kwargs)  # type: MediaForgeProtocol
        return forge.create_media(media_spec)

    # ------------
    # api
    # ------------

    @classmethod
    def clear_media_resource(cls,
                             node: MediaNode):
        # could clean it entirely out of the registry, but not sure what
        # the real use case is for this
        node.rit = None

    @classmethod
    def prepare_media_resource(cls,
                               node: MediaNode,
                               spec_overrides: dict = None,
                               forge_kwargs: dict = None) -> bool:
        # This method may mutate the media node's rit and spec fields

        if node.url or node.data or node.rit:
            # No need to do anything
            return True

        if rit := cls._rit_from_alias(node):
            # Try to find it under any aliases
            return True

        if node.spec:
            # Try to create it with a media forge
            rit = cls._rit_from_spec(node,
                                     spec_overrides=spec_overrides,
                                     forge_kwargs=forge_kwargs)
            if rit:
                return True

        return False
        # raise RuntimeError(f"Unable to prepare data for {node}!")

    @classmethod
    def get_media_resource(cls,
                           node: MediaNode,
                           spec_overrides: dict = None,
                           forge_kwargs: dict = None) -> JournalMediaItem:

        # Already prepared
        if node.url:
            # pass through url
            return cls._resource_from_external(node)
        elif node.data:
            # pass through data
            return cls._resource_from_data(node)
        elif node._rit:
            # already prepared the media
            return cls._resource_from_rit(node)

        # Try to prepare (find or create) the media resource
        cls.prepare_media_resource(node, spec_overrides, forge_kwargs)
        if node._rit:
            return cls._resource_from_rit(node)


class HasMedia:
    """
    Mixin for a parent Node that has MediaNode children.
    """

    @property
    def media(self: Node) -> list[MediaNode]:
        return self.find_children(MediaNode)


