from .enums import MediaDataType
from .media_resource_inventory_tag import MediaResourceInventoryTag
from .media_resource_registry import MediaResourceRegistry, on_index_media
from .media_resource import MediaDep, on_provision_media
from .media_fragment import MediaFragment, StagingHints
from .media_spec import MediaSpec, on_adapt_media_spec

# Ensure default indexing handlers are registered when importing the package.
from . import indexing as _indexing_handlers  # noqa: F401
