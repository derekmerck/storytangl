# media-specific type hints

from PIL.Image import Image
Svg = str
Audio = tuple[bytes, dict]

Media = Image | Svg | Audio | bytes

# Media = Image | Audio | bytes | str

