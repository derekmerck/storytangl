"""Hash stability contract — see ``design/core/CONTENT_ADDRESSABLE.md``.

``content_hash`` and ``value_hash`` must be reproducible across processes, because they
are content identity and may be persisted. ``id_hash`` deliberately is not: it backs
``__eq__`` within a single interpreter and never reaches serialization.

The interesting failure mode is silent. Set iteration order for strings varies with
``PYTHONHASHSEED``, so a set-valued field — ``tags`` is on *every* entity — made
``value_hash`` differ on every run while every single-process test still passed. These
tests therefore run real subprocesses under different hash seeds; an in-process test
cannot observe the bug at all.
"""

from __future__ import annotations

import subprocess
import sys
import textwrap

import pytest

from tangl.core import Node
from tangl.utils.hashing import hashing_func


SEEDS = ("0", "1", "42", "12345")


def _run_under_seed(body: str, seed: str) -> str:
    """Execute ``body`` in a fresh interpreter with a fixed PYTHONHASHSEED."""
    result = subprocess.run(
        [sys.executable, "-c", textwrap.dedent(body)],
        capture_output=True,
        text=True,
        env={"PYTHONHASHSEED": seed, "PATH": ""},
        timeout=120,
    )
    if result.returncode != 0:
        pytest.fail(f"subprocess (seed={seed}) failed:\n{result.stderr}")
    return result.stdout.strip()


ENTITY_SNIPPET = """
    import uuid
    from tangl.core import Node
    n = Node(
        label="probe",
        uid=uuid.UUID("00000000-0000-0000-0000-0000000000ab"),
        tags={"alpha", "beta", "gamma", "delta", "epsilon"},
    )
    print(n.value_hash().hex())
"""


class TestCrossProcessStability:
    """The guarantees that may be written to disk."""

    def test_value_hash_is_identical_under_different_hash_seeds(self):
        digests = {seed: _run_under_seed(ENTITY_SNIPPET, seed) for seed in SEEDS}
        assert len(set(digests.values())) == 1, (
            f"value_hash varies with PYTHONHASHSEED — set ordering leaked: {digests}"
        )

    def test_tags_serialize_as_a_sorted_list(self):
        digests = {
            seed: _run_under_seed(
                """
                from tangl.core import Node
                print(Node(label="p", tags={"delta", "alpha", "charlie", "bravo"})
                      .unstructure()["tags"])
                """,
                seed,
            )
            for seed in SEEDS
        }
        assert set(digests.values()) == {"['alpha', 'bravo', 'charlie', 'delta']"}, digests

    def test_template_content_hash_is_identical_under_different_hash_seeds(self):
        digests = {
            seed: _run_under_seed(
                """
                import uuid
                from tangl.core import Node
                from tangl.core.template import EntityTemplate
                n = Node(
                    label="goblin",
                    uid=uuid.UUID("00000000-0000-0000-0000-0000000000cd"),
                    tags={"hostile", "cave", "small"},
                )
                print(EntityTemplate(payload=n).content_hash().hex())
                """,
                seed,
            )
            for seed in SEEDS
        }
        assert len(set(digests.values())) == 1, (
            f"content_hash varies with PYTHONHASHSEED: {digests}"
        )


class TestSetNormalization:
    """In-process properties that hold regardless of seed."""

    def test_insertion_order_does_not_change_the_dump(self):
        forward = Node(label="p", tags={"zebra", "apple", "mango"})
        backward = Node(label="p", tags=set())
        for tag in ("mango", "zebra", "apple"):
            backward.tags.add(tag)

        assert forward.unstructure()["tags"] == backward.unstructure()["tags"]

    def test_sorted_list_round_trips_back_to_a_set(self):
        node = Node(label="p", tags={"b", "a"})
        restored = Node.structure(node.unstructure())
        assert restored.tags == {"a", "b"}
        assert isinstance(restored.tags, set)

    def test_distinct_tag_sets_still_differ(self):
        a = Node(label="p", uid=Node(label="x").uid, tags={"one"})
        b = a.evolve(tags={"two"})
        assert a.value_hash() != b.value_hash()


class TestIdHashIsDeliberatelyProcessLocal:
    """``id_hash`` is runtime identity — the contract is that it is *not* portable."""

    def test_id_hash_varies_across_processes(self):
        digests = {
            seed: _run_under_seed(
                """
                import uuid
                from tangl.core import Node
                print(Node(label="probe",
                           uid=uuid.UUID("00000000-0000-0000-0000-0000000000ab")
                     ).id_hash().hex())
                """,
                seed,
            )
            for seed in SEEDS
        }
        assert len(set(digests.values())) > 1, (
            "id_hash became stable across processes. That is not a bug, but the "
            "contract in CONTENT_ADDRESSABLE.md says it is process-local and callers "
            "were told never to persist it — reconcile the doc before relying on this."
        )

    def test_id_hash_backs_equality_within_a_process(self):
        node = Node(label="probe")
        twin = node.model_copy()
        assert node.eq_by_id(twin) and node == twin

    def test_id_hash_never_reaches_serialization(self):
        node = Node(label="probe", tags={"a"})
        data = node.unstructure()
        assert node.id_hash() not in data.values()
        assert not any(isinstance(v, (bytes, bytearray)) for v in data.values())

    def test_class_object_hashing_is_the_unstable_path(self):
        """Pins *why*: a class passed top-level falls through to builtin ``hash()``."""
        digests = {
            seed: _run_under_seed(
                """
                from tangl.core import Node
                from tangl.utils.hashing import hashing_func
                print(hashing_func(Node, "fixed").hex(), hashing_func("Node", "fixed").hex())
                """,
                seed,
            )
            for seed in SEEDS
        }
        as_class = {d.split()[0] for d in digests.values()}
        as_string = {d.split()[1] for d in digests.values()}
        assert len(as_class) > 1, "class-object hashing should be process-local"
        assert len(as_string) == 1, "string hashing must be stable"
