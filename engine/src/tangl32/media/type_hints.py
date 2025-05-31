# media-specific type hints

from PIL.Image import Image
Svg = str

Media = Image | Svg | bytes

# Audio = tuple[bytes, dict]
# Media = Image | Audio | bytes | str

