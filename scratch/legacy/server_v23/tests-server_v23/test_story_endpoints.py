import pytest
from fastapi.testclient import TestClient
from tangl.rest.app import app

client = TestClient(app, base_url="http://tangl/api/v2/")

@pytest.mark.xfail(reason="requires story manager api")
def test_get_update():
    response = client.get("story/update")
    assert response.status_code == 200
    update = response.json()
    assert "text" in update[0]
    assert update[0]["text"] == "You are at the start."

@pytest.mark.xfail(reason="requires story manager api")
def test_do_action():
    response = client.post("story/action", json={"uid": "scene_1/block_1/action_1"})
    assert response.status_code == 200
    update = response.json()
    assert "text" in update[0]
    assert update[0]["text"] == "You are in block 2."

    with pytest.raises(ValueError):
        # no longer available in bookmark
        response = client.post("/story/action", json={"uid": "scene_1/block_1/action_1"})

@pytest.mark.skip(reason="Requires story manager api")
def test_get_story_status():
    response = client.get("story/status")
    assert response.status_code == 200
    status = response.json()
    assert "label" in status[0]

@pytest.mark.xfail(reason="requires story manager api")
def test_reset_story():
    response = client.delete("story/drop")
    assert response.status_code == 200
    update = response.json()
    assert "text" in update[0]
    assert update[0]["text"] == "You are at the start."


@pytest.mark.xfail(reason="requires story manager api")
def test_simple_persistence():

    response = client.post("dev/eval", json={"expr": "var1"})
    assert response.status_code != 200
    res = response.json()
    assert res['errors']

    response = client.post("dev/exec", json={"expr": "var1 = True"})
    assert response.status_code == 200
    res = response.json()
    assert res['response'] == "ok"

    response = client.post("dev/eval", json={"expr": "var1"})
    assert response.status_code == 200
    res = response.json()
    assert res['result'] is True

# There is no longer any reason to use this, but it was an interesting way to
# quickly mock out calls to all the api keys before switching to a config manager.

# def test_app_funcs():
#
#     SECRET = "TEST_TEST_TEST"
#     api_key = controllers.do_get_api_key(SECRET)['api_key']
#     print(api_key)
#     api_key2 = controllers.do_get_api_key()
#     print(api_key2)
#
#     kwargs_ = {
#         "secret": SECRET,
#         'token_info': {'api_key': api_key},
#         'wo_': 'sample',
#         'sc_': 'main_menu',
#         'blk_': 'start',
#         'uid': {
#             'do_inspect': 'main_menu',
#             'do_do_action': 'main_menu/start/ac0',
#             'do_get_resource_image': 'sample_person',
#             'do_get_scene_image': 'general/logo'
#         },
#         "grp_": "general",
#         "im_": "logo",
#         "body": {
#             'do_exec': {"expr": "turn = 5"},
#             'do_eval': {"expr": "turn == 5"}
#         },
#     }
#
#     for k, v in inspect.getmembers(controllers,
#                                    lambda x: callable(x) and
#                                              hasattr(x, "__name__") and
#                                              x.__name__.startswith("do")):
#         print(f"\nTesting {k}")
#         print(inspect.signature(v))
#
#         kwargs = {}
#         for kk in inspect.signature(v).parameters:
#             if kk in kwargs_:
#                 val = kwargs_[kk]
#                 if isinstance(val, dict) and k in val:
#                     val = val[k]
#                 kwargs[kk] = val
#
#         print(kwargs)
#
#         try:
#             res = v(**kwargs)
#             print(res)
#         except (StoryAccessError, KeyError) as e:
#             print(f"ignoring ctx error {e}")

