import re
import unicodedata

_SANITIZE_RE = re.compile(r"[^0-9a-zA-Z_]+")


def sanitize_path(path: str) -> str:
    """
    Sanitize a label or qualified path.

    Examples:
        "0" → "_0"
        "garden.entrance" → "garden.entrance" (already safe)
        "123.0a" → "_123._0a"
    """
    segments = path.split(".")
    sanitized_segments = [sanitize_str(seg) for seg in segments]
    return ".".join(sanitized_segments)


def sanitize_str(value: str) -> str:
    """
    Turn *value* into a valid Python identifier for StringMap type.

    * replace illegal chars with '_'      →  "little-dog"  →  "little_dog"
    * prefix '_' if it would start with # →  "123abc"      →  "_123abc"
    """
    if not isinstance(value, str):
        return value
    value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('utf8')
    value = _SANITIZE_RE.sub("_", value)
    value = re.sub("__", "_", value)  # get rid of double __
    if value and value[0].isdigit():
        value = f"_{value}"
    return value or "_"
