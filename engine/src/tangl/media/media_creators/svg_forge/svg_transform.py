from __future__ import annotations

class SvgTransform:
    def __init__(self, transforms: list[str] = None):
        self.transforms = transforms if transforms else []

    def translate(self, x: float, y: float):
        self.transforms.append(f"translate({x} {y})")
        return self

    def scale(self, x: float, y: float = None):
        if y is None:
            y = x
        self.transforms.append(f"scale({x} {y})")
        return self

    def __str__(self) -> str:
        return ' '.join(self.transforms)
