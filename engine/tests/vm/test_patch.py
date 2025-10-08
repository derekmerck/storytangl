from __future__ import annotations

import uuid

import pytest

from tangl.core import Graph
from tangl.vm.replay import Patch


def test_patch_apply_allows_matching_registry():
    graph = Graph(label="demo")
    applied = Patch(registry_id=graph.uid, registry_state_hash=graph._state_hash(), events=[]).apply(graph)
    assert applied is not graph
    assert applied.unstructure() == graph.unstructure()


def test_patch_apply_validates_registry_id():
    graph = Graph(label="demo")
    patch = Patch(registry_id=uuid.uuid4(), registry_state_hash=graph._state_hash(), events=[])
    with pytest.raises(ValueError):
        patch.apply(graph)


def test_patch_apply_validates_state_hash():
    graph = Graph(label="demo")
    patch = Patch(registry_id=graph.uid, registry_state_hash=b"wrong", events=[])
    with pytest.raises(ValueError):
        patch.apply(graph)
