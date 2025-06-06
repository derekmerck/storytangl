from PIL import Image

from tangl.info import __title__, __author__, __author_email__, __url__, __version__
from . import __version__ as __forge_version__, __title__ as __forge_title__

def basic_info() -> dict:
    return {
        "tool": f"{__forge_title__} v{__forge_version__}",
        "creator": __author__,       # override with domain author?
        "email": __author_email__,   # override with domain author?
        "url": __url__,              # override with client relative url?
        "collection": None,          # todo: this should be the domain/world and version
        "source": f"{__title__} v{__version__}"
    }

DEFAULT_MAX_DIM = 1200

def dims_given_max(im: Image, max_dim=DEFAULT_MAX_DIM) -> tuple[int, int]:
    if im.width > im.height:
        aspect_ratio = im.height / im.width
        return (max_dim, int(max_dim * aspect_ratio))
    else:
        aspect_ratio = im.width / im.height
        return (int(max_dim * aspect_ratio), max_dim)
