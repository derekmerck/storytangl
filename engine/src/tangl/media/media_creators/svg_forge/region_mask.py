"""Build explicit, opaque visible-region masks on a registered SVG tree."""
from __future__ import annotations

from lxml import etree


def _style(element: etree._Element) -> dict[str, str]:
    return {key.strip(): value.strip() for part in element.get("style", "").split(";")
            if ":" in part for key, value in [part.split(":", 1)]}


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
    for identifier in (*targets, *occluders):
        if len(root.xpath("//*[@id=$id]", id=identifier)) != 1:
            raise ValueError(f"Missing or ambiguous region geometry: {identifier}")
    shapes = {"path", "rect", "circle", "ellipse", "polygon", "polyline"}
    for element in root.iter():
        if not isinstance(element.tag, str):
            continue
        name = etree.QName(element).localname
        if name == "style":
            element.text = ""
            continue
        if any(etree.QName(parent).localname in {"defs", "clipPath", "mask"}
               for parent in element.iterancestors()):
            continue
        if name in {"use", "image", "text", "foreignObject", "line"}:
            element.set("style", "display:none")
            continue
        if name not in shapes and name != "g":
            continue
        owner = next((item.get("id") for item in (element, *element.iterancestors())
                      if item.get("id") in targets or item.get("id") in occluders), None)
        style = _style(element)
        if name == "g":
            if owner is not None:
                style.update({"opacity": "1", "mix-blend-mode": "normal", "filter": "none"})
                element.set("style", ";".join(f"{key}:{value}" for key, value in style.items()))
            continue
        fill = next((paint for node in (element, *element.iterancestors())
                     if (paint := _style(node).get("fill", node.get("fill"))) is not None), "black")
        if owner is None or fill == "none":
            element.set("style", "display:none")
            continue
        color = "white" if targets.get(owner) == region else "black"
        style.update({"fill": color, "fill-opacity": "1", "opacity": "1", "stroke": "none",
                      "mix-blend-mode": "normal", "filter": "none", "marker-start": "none",
                      "marker-mid": "none", "marker-end": "none"})
        element.set("style", ";".join(f"{key}:{value}" for key, value in style.items()))
    return etree.tostring(root, encoding="unicode")
