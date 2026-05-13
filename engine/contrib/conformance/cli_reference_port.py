#!/usr/bin/env python3
"""Render StoryTangl conformance fixtures as a plain terminal client."""

from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Sequence


def _load_reference_port() -> ModuleType:
    try:
        import reference_port

        return reference_port
    except ModuleNotFoundError as error:
        if error.name != "reference_port":
            raise
        module_path = Path(__file__).with_name("reference_port.py")
        spec = importlib.util.spec_from_file_location("reference_port", module_path)
        if spec is None or spec.loader is None:
            raise
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module


_REFERENCE_PORT = _load_reference_port()

load_fixture = _REFERENCE_PORT.load_fixture
render_fixture = _REFERENCE_PORT.render_fixture
render_fixture_document = _REFERENCE_PORT.render_fixture_document
format_document = _REFERENCE_PORT.format_document


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("fixture", type=Path, help="Path to a conformance fixture JSON file")
    args = parser.parse_args(argv)

    for line in render_fixture(load_fixture(args.fixture)):
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
