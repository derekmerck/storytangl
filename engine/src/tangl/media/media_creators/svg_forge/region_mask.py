"""Build explicit, opaque visible-region masks on a registered SVG tree."""
from __future__ import annotations

from lxml import etree

_SHAPES = {"path", "rect", "circle", "ellipse", "polygon", "polyline"}
_UNSUPPORTED = {"use", "image", "text", "foreignObject", "line"}
_DEFINITIONS = {"defs", "clipPath", "mask"}


def _style(element: etree._Element) -> dict[str, str]:
    return {key.strip(): value.strip() for part in element.get("style", "").split(";")
            if ":" in part for key, value in [part.split(":", 1)]}


def _paint(element: etree._Element, property: str, default: str) -> str:
    for node in (element, *element.iterancestors()):
        value = _style(node).get(property, node.get(property))
        if value is None:
            continue
        value = value.replace("!important", "").strip().lower()
        if value in {"inherit", "unset"}:
            continue
        return default if value == "initial" else value
    return default


def region_fill_coverage(root: etree._Element, identifiers: tuple[str, ...]) -> tuple[bool, bool]:
    """Report whether nominated geometry has supported fills and unsupported paint."""
    supported = unsupported = False
    for identifier in identifiers:
        groups = root.xpath("//*[@id=$id]", id=identifier)
        if len(groups) != 1:
            raise ValueError(f"Missing or ambiguous region geometry: {identifier}")
        for element in groups[0].iter():
            if not isinstance(element.tag, str):
                continue
            if any(etree.QName(parent).localname in _DEFINITIONS for parent in element.iterancestors()):
                continue
            name = etree.QName(element).localname
            if name in _UNSUPPORTED:
                unsupported = True
            elif name in _SHAPES:
                supported |= _paint(element, "fill", "black") != "none"
                unsupported |= _paint(element, "stroke", "none") != "none"
    return supported, unsupported


def region_mask_svg(source: str, *, regions: dict[str, tuple[str, ...]],
                    occluders: tuple[str, ...], region: str) -> str:
    """Paint nominated regions white and opaque foreground occluders black.

    The red channel, multiplied by alpha, is the mask value. Geometry outside
    the explicit nominations is excluded; source order, transforms and clips
    are retained. This bounded path treats nominated paint as opaque fills.
    """
    if region not in regions or not regions[region]:
        raise ValueError(f"Missing region coverage: {region}")
    root = etree.fromstring(source.encode(), etree.XMLParser(resolve_entities=False, no_network=True))
    targets = {identifier: name for name, ids in regions.items() for identifier in ids}
    if len(targets) != sum(len(ids) for ids in regions.values()):
        raise ValueError("A shape group cannot belong to multiple regions")
    if set(targets) & set(occluders) or len(set(occluders)) != len(occluders):
        raise ValueError("Region and occluder groups must be distinct")
    nominated = []
    for identifier in (*targets, *occluders):
        matches = root.xpath("//*[@id=$id]", id=identifier)
        if len(matches) != 1:
            raise ValueError(f"Missing or ambiguous region geometry: {identifier}")
        nominated.append(matches[0])
    wrappers = {ancestor for item in nominated for ancestor in item.iterancestors()}
    for element in root.iter():
        if not isinstance(element.tag, str):
            continue
        name = etree.QName(element).localname
        if name == "style":
            element.text = ""
            continue
        if any(etree.QName(parent).localname in _DEFINITIONS
               for parent in element.iterancestors()):
            continue
        if name in _UNSUPPORTED:
            element.set("style", "display:none")
            continue
        owner = next((item.get("id") for item in (element, *element.iterancestors())
                      if item.get("id") in targets or item.get("id") in occluders), None)
        style = _style(element)
        if name not in _SHAPES:
            if owner is not None or element in wrappers:
                style.update({"opacity": "1", "mix-blend-mode": "normal", "filter": "none", "mask": "none"})
                element.set("style", ";".join(f"{key}:{value}" for key, value in style.items()))
            continue
        if owner is None or _paint(element, "fill", "black") == "none":
            element.set("style", "display:none")
            continue
        color = "white" if targets.get(owner) == region else "black"
        style.update({"fill": color, "fill-opacity": "1", "opacity": "1", "stroke": "none",
                      "mix-blend-mode": "normal", "filter": "none", "mask": "none", "marker-start": "none",
                      "marker-mid": "none", "marker-end": "none"})
        element.set("style", ";".join(f"{key}:{value}" for key, value in style.items()))
    return etree.tostring(root, encoding="unicode")
