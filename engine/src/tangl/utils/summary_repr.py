from typing import Any, Mapping


def summary_repr(value: Any, max_len=40, max_items=3) -> str:
    """
    Terse, human-readable representation of data for logging
    """

    # 1. If the object has its own short summary method, use it.
    if hasattr(value, 'summary_repr') and callable(value.summary_repr):
        try:
            return value.summary_repr(maxlen=max_len, max_items=max_items)
        except TypeError:
            # For legacy or simpler signatures, just call with no arguments.
            return value.summary_repr()

    # 2. Simple scalars and bool
    if isinstance(value, (int, float, bool, type(None))):
        return repr(value)

    # 3. Short strings
    if isinstance(value, str):
        s = value if len(value) <= max_len else value[:max_len] + "…"
        return f"'{s}'"

    # 4. Short mappings (dict, ChainMap)
    if isinstance(value, Mapping):
        items = list(value.items())
        items_str = ", ".join(f"{k}: {summary_repr(v, max_len=20)}" for k, v in items[:max_items])
        if len(items) > max_items:
            items_str += ", …"
        return "{" + items_str + "}"

    # 5. Short lists/tuples
    if isinstance(value, (list, tuple)):
        items_str = ", ".join(summary_repr(v, max_len=20) for v in value[:max_items])
        if len(value) > max_items:
            items_str += ", …"
        return "[" + items_str + "]"

    # 6. Binary-like (bytes, bytearray)
    if isinstance(value, (bytes, bytearray)):
        return f"<{len(value)} bytes>"

    # Other complex types

    # # 8. PIL.Image
    # try:
    #     from PIL import Image
    #     if isinstance(value, Image.Image):
    #         return f"<PIL.Image size={value.size}>"
    # except ImportError:
    #     pass
    #
    # # 7. XML-like
    # if hasattr(value, "tag") and hasattr(value, "attrib"):  # e.g., xml.etree.Element
    #     return f"<XML tag='{getattr(value, 'tag', '?')}'…>"

    # 8. Fallback: type name
    return f"<{type(value).__name__}>"

