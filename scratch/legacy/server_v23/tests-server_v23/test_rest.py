"""
Only tests that the OA3 spec load and find all
its endpoints properly, so not exhaustive.
"""

from pprint import pprint
from flask import Response
from legacy.rest.app import create_app

import pytest


@pytest.fixture(scope='module')
def client():
    flask_app = create_app()
    with flask_app.test_client() as c:
        yield c


def test_content(client, wo_: str = "sample_world"):
    url = f'/api/2.3/public/info/{wo_}'
    r: Response = client.get(url)
    pprint(r.json)
    assert r.status_code == 200


if __name__ == "__main__":
    flask_app = create_app()
    client = flask_app.test_client()
    test_content(client, "sample")
