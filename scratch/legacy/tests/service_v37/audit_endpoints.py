"""Manual audit helper for controller response alignment."""

from __future__ import annotations

from typing import Any, get_type_hints

from tangl.service.api_endpoint import ResponseType
from tangl.service.controllers import RuntimeController, SystemController, UserController, WorldController

EXPECTED_TYPES = {
    ResponseType.CONTENT: "list[BaseFragment]",
    ResponseType.INFO: "InfoModel subclass",
    ResponseType.RUNTIME: "RuntimeInfo",
    ResponseType.MEDIA: "MediaFragment",
}


def audit_all_endpoints() -> list[tuple[str, str, ResponseType, object]]:
    """Print a report of annotated endpoints and their return annotations."""

    print("Endpoint Response Contract Audit")
    print("=" * 80)

    controllers = [
        RuntimeController,
        UserController,
        SystemController,
        WorldController,
    ]

    issues: list[tuple[str, str, ResponseType, object]] = []

    for ctrl_cls in controllers:
        endpoints = ctrl_cls.get_api_endpoints()

        for name, endpoint in endpoints.items():
            hints = _safe_type_hints(endpoint.func)
            return_type = hints.get("return", type(None))

            aligned = _check_alignment(endpoint.response_type, return_type)
            marker = "✓" if aligned else "✗"

            expected = EXPECTED_TYPES[endpoint.response_type]
            actual = str(return_type)

            print(f"{marker} {ctrl_cls.__name__}.{name}")
            print(f"   response_type={endpoint.response_type.value}")
            print(f"   return_type={actual}")
            print(f"   expected={expected}\n")

            if not aligned:
                issues.append((ctrl_cls.__name__, name, endpoint.response_type, return_type))

    print("=" * 80)
    print(f"Total issues: {len(issues)}")

    if issues:
        print("\nFix these:")
        for ctrl, method, resp_type, ret_type in issues:
            print(f"  - {ctrl}.{method}: {ret_type} → {EXPECTED_TYPES[resp_type]}")

    return issues


def _safe_type_hints(func: Any) -> dict[str, object]:
    try:
        return get_type_hints(func)
    except Exception:
        # Fallback when annotations cannot be resolved
        return getattr(func, "__annotations__", {}) or {}


def _check_alignment(response_type: ResponseType, return_type: object) -> bool:
    text = str(return_type).lower()
    if response_type == ResponseType.CONTENT:
        return "basefragment" in text or "fragment" in text
    if response_type == ResponseType.INFO:
        return "info" in text and "runtimeinfo" not in text
    if response_type == ResponseType.RUNTIME:
        return "runtimeinfo" in text
    if response_type == ResponseType.MEDIA:
        return "media" in text
    return False


if __name__ == "__main__":
    audit_all_endpoints()
