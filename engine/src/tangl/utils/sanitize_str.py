import re
import unicodedata

_SANITISE_RE = re.compile(r"[^0-9a-zA-Z_]+")


def sanitise_str(value: str) -> str:
    """
    Turn *value* into a valid Python identifier for StringMap type.

    * replace illegal chars with '_'      →  "little-dog"  →  "little_dog"
    * prefix '_' if it would start with # →  "123abc"      →  "_123abc"
    """
    if not isinstance(value, str):
        return value
    value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('utf8')
    value = _SANITISE_RE.sub("_", value)
    value = re.sub("__", "_", value)  # get rid of double __
    if value and value[0].isdigit():
        value = f"_{value}"
    return value or "_"
