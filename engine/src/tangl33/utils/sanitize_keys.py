import re

_SANITISE_RE = re.compile(r"[^0-9a-zA-Z_]+")

def _sanitise(key: str) -> str:
    """
    Turn *key* into a valid Python identifier:

    * replace illegal chars with '_'      →  "little-dog"  →  "little_dog"
    * prefix '_' if it would start with # →  "123abc"      →  "_123abc"
    """
    key = _SANITISE_RE.sub("_", key)
    if key and key[0].isdigit():
        key = f"_{key}"
    return key or "_"
