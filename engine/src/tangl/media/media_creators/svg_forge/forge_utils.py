from PIL import Image

from tangl.info import __title__, __author__, __author_email__, __url__, __version__
from . import __version__ as __forge_version__, __title__ as __forge_title__

# todo: maybe should indicate template type, like forge v + card, paperdoll, etc. as tool?
#       move storytangl -> creator/url
#       collection, author as domain

def basic_info() -> dict:
    return {
        "tool": f"{__forge_title__} v{__forge_version__}",
        "creator": __author__,       # override with domain author?
        "email": __author_email__,   # override with domain author?
        "url": __url__,              # override with client relative url?
        "collection": None,          # todo: this should be the domain/world and version
        "source": f"{__title__} v{__version__}"
    }
