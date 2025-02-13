from tangl.info import __version__

# schema version can be tied to library minor version
minor_version = ".".join(__version__.split(".")[0:1])  # i.e "3.2"
RESPONSE_SCHEMA_VERSION = minor_version

from .response_models import ContentResponse, InfoResponse
from .presentation_hints import PresentationHints
from .base_fragment import ResponseFragment, ResponseFragmentUpdate
from .text_fragment import TextResponseFragment
from .media_fragment import MediaResponseFragment, MediaResponseFragmentUpdate, MediaPresentationHints
from .kv_fragment import KvResponseFragment
