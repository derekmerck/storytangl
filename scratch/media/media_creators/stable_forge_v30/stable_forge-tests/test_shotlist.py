import pytest
import yaml

from tangl.media.illustrated.stableforge2.stableforge_specs import Auto1111Spec as StableForgeSpec
from tangl.media.illustrated.stableforge.shotlist import make_shotlist, load_shotlist

@pytest.fixture
def shot_types() -> dict:
    shot_types = {
        'boat': {
            'seed': 100,
            'prompt': '{{ role.actor }} standing on a boat {{ loc.text }}',
            'neg_prompt': 'a little {{ animal }}',
            'animal': 'cat',
            'hi_res': {
                'scale': 2.0
            }
        }
    }
    return shot_types

@pytest.fixture
def shot_vars() -> dict:
    shot_vars = {
        'role': {
            'person1': {
                'actor': 'abc'
            },
            'person2': {
                'actor': 'def'
            }
        },
        'loc': {
            'ocean': {
                'text': 'in the stormy ocean'
            }
        }
    }
    return shot_vars


def test_make_shotlist_basic(shot_types, shot_vars):

    shot_configs = {
        'boat-person1-ocean': {
            'shot_type': 'boat',
            'role': 'person1',
            'loc': 'ocean',
            'animal': 'dog'
        }
    }

    expected_result = [
        StableForgeSpec(
            uid='boat-person1-ocean',
            prompt='abc standing on a boat in the stormy ocean',
            neg_prompt="a little dog",
            seed=100,
        )
    ]

    res = make_shotlist(shot_types, shot_vars, shot_configs)
    assert res == expected_result
    assert [r.uid for r in res] == [e.uid for e in expected_result]

def test_update_uid(shot_types, shot_vars):
    shot_configs = {
        'dummy': {
            'uid': '{{ shot_type}}-{{ role }}-{{ loc }}',
            'shot_type': 'boat',
            'role': 'person1',
            'loc': 'ocean',
        }
    }
    expected_result = [
        StableForgeSpec(
            uid='boat-person1-ocean',
            prompt='abc standing on a boat in the stormy ocean',
            neg_prompt="a little cat",
            seed=100,
        )
    ]

    res = make_shotlist(shot_types, shot_vars, shot_configs)
    assert res == expected_result
    assert [r.uid for r in res] == [e.uid for e in expected_result]

def test_dereference_from_uid(shot_types, shot_vars):
    # omit role, should still read it from uid
    shot_configs = {
        'boat-person1-ocean': {
            'shot_type': 'boat',
            'loc': 'ocean',
        }
    }
    expected_result = [
        StableForgeSpec(
            uid='boat-person1-ocean',
            prompt='abc standing on a boat in the stormy ocean',
            neg_prompt="a little cat",
            seed=100,
        )
    ]

    res = make_shotlist(shot_types, shot_vars, shot_configs)
    assert res == expected_result
    assert [r.uid for r in res] == [e.uid for e in expected_result]

def test_generate_multiple(shot_types, shot_vars):
    # should generate 2
    shot_configs = {
        'boat-someone-ocean': {
            'shot_type': 'boat',
            'role': ['person1', 'person2'],
            'loc': 'ocean',
            'animal': 'dog'
        }
    }
    expected_result = [
        StableForgeSpec(
            uid='boat-someone-ocean',
            prompt='abc standing on a boat in the stormy ocean',
            neg_prompt="a little dog",
            seed=100,
        ),
        StableForgeSpec(
            uid='boat-someone-ocean',
            prompt='def standing on a boat in the stormy ocean',
            neg_prompt="a little dog",
            seed=100,
        ),
    ]
    res = make_shotlist(shot_types, shot_vars, shot_configs)
    assert res == expected_result
    assert [r.uid for r in res] == [e.uid for e in expected_result]

def test_generate_multiple_and_update_uids(shot_types, shot_vars):
    # should generate 2 and update the uid's
    shot_configs = {
        'dummy': {
            'uid': 'boat-{{ role }}-{{ loc }}',
            'shot_type': 'boat',
            'role': ['person1', 'person2'],
            'loc': 'ocean',
            'animal': 'dog'
        }
    }
    expected_result = [
        StableForgeSpec(
            uid='boat-person1-ocean',
            prompt='abc standing on a boat in the stormy ocean',
            neg_prompt="a little dog",
            seed=100,
        ),
        StableForgeSpec(
            uid='boat-person2-ocean',
            prompt='def standing on a boat in the stormy ocean',
            neg_prompt="a little dog",
            seed=100,
        ),
    ]
    res = make_shotlist(shot_types, shot_vars, shot_configs)
    assert res == expected_result
    assert [r.uid for r in res] == [e.uid for e in expected_result]


def test_make_shotlist_error(shot_types, shot_vars):

    shot_configs = {
        'boat-person1-ocean': {
            'shot_type': 'boat',
            'role': 'person1',
            'loc': 'ocean'
        },
        'missing-variables': {
            'shot_type': 'boat',
            'role': 'person3',
            'loc': 'ocean'
        }
    }

    with pytest.raises(KeyError):
        make_shotlist(shot_types, shot_vars, shot_configs)

def test_load_shotlist(tmpdir, shot_types, shot_vars):

    shot_configs = {
        'boat-person1-ocean': {
            'shot_type': 'boat',
            'role': 'person1',
            'loc': 'ocean'
        }
    }
    data = {'shot_types': shot_types,
            'shot_vars': shot_vars,
            'shot_configs': shot_configs}

    yaml_file = tmpdir / 'shotlist.yaml'

    with open(yaml_file, 'w') as f:
        yaml.safe_dump(data, f)

    expected_result = [
        StableForgeSpec(
            uid='boat-person1-ocean',
            prompt='abc standing on a boat in the stormy ocean',
            neg_prompt = 'a little cat',
            seed=100,
        )
    ]

    res = load_shotlist(yaml_file)
    assert res == expected_result
    assert [r.uid for r in res] == [e.uid for e in expected_result]
