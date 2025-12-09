# tangl/cl_utils/info.py
from __future__ import annotations

import sys

from tangl.service.controllers.system_controller import SystemController


def main() -> int:
    """
    Usage:
    $ python -m tangl.cl_utils.info  # on PYTHONPATH --or--
    $ tangl-info                     # using installed script entry point

    One-shot health/info command:

    - invokes the PUBLIC system.get_system_info endpoint
    - prints a JSON payload to stdout
    - exits 0 on success, nonzero on failure
    """
    try:
        info = SystemController.get_system_info()
    except Exception as exc:  # noqa: BLE001
        print(f"[FAIL] system.get_system_info errored: {exc!r}", file=sys.stderr)
        return 1

    # SystemInfo is a Pydantic model; use its serializer.
    try:
        payload = info.model_dump()  # Pydantic v2
    except AttributeError:
        # if you ever run this on v1
        payload = info.dict()

    import yaml
    print(yaml.dump(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())