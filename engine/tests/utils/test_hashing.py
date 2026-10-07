"""Canonical unordered hashing without changing ordered collection semantics."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from hashlib import sha224
from typing import Any

import pytest

from tangl.utils.hashing import hashing_func


@pytest.mark.parametrize("kind", [set, frozenset])
@pytest.mark.parametrize("digest_size", [None, 16])
def test_unordered_collections_hash_their_sorted_values(
    kind: type[set[str]] | type[frozenset[str]], digest_size: int | None,
) -> None:
    values = kind(["beta", "alpha"])
    expected = hashing_func({"values": ["alpha", "beta"]}, digest_size=digest_size)
    assert hashing_func({"values": values}, digest_size=digest_size) == expected
    assert hashing_func(values, digest_size=digest_size) == hashing_func(
        kind(["alpha", "beta"]), digest_size=digest_size,
    )
    assert hashing_func(values, digest_size=digest_size) != hashing_func(
        kind(["alpha", "gamma"]), digest_size=digest_size,
    )


@pytest.mark.parametrize("kind", [list, tuple])
def test_ordered_collection_order_remains_significant(
    kind: type[list[Any]] | type[tuple[Any, ...]],
) -> None:
    assert hashing_func({"values": kind(["alpha", "beta"])}) != hashing_func(
        {"values": kind(["beta", "alpha"])},
    )


def test_mapping_without_sets_retains_its_existing_digest() -> None:
    payload = {"second": [1, 2], "first": "unchanged"}
    salt = b"hashing regression"
    expected = sha224(salt + json.dumps(payload, default=str, sort_keys=True).encode()).digest()
    assert hashing_func(payload, salt=salt) == expected
    assert hashing_func(dict(reversed(list(payload.items()))), salt=salt) == expected


def test_nested_unordered_collections_hash_identically_across_processes() -> None:
    code = (
        "from tangl.utils.hashing import hashing_func; "
        "payload = {'groups': [{'tags': {'event', 'interaction:now', "
        "'interaction', 'sandbox', 'dynamic'}}], "
        "'mixed': frozenset({1, '1', ('beta', 'alpha'), frozenset({'x', 'y'})})}; "
        "print(hashing_func(payload, salt=b'regression').hex())"
    )
    digests = {
        subprocess.check_output(
            [sys.executable, "-c", code],
            env={**os.environ, "PYTHONHASHSEED": str(seed)},
            text=True,
        ).strip()
        for seed in (0, 11, 37)
    }
    assert len(digests) == 1
