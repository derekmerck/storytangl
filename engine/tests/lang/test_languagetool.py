"""
Example of using this to mark other tests as xfail or ignore

import pytest

@pytest.fixture(scope="session", autouse=True)
def check_languagetool():
    try:
        # Here, run the code that checks if the LanguageTool node is up
        # If it's not up, this will raise an exception
        test_languagetool_node()
        return True
    except:
        return False

@pytest.mark.dynamic_xfail
def test_something_else(check_languagetool):
    if not check_languagetool:
        pytest.xfail("LanguageTool node is not running.")
    # Rest of your test code here

"""
import pytest
import requests

from tangl.config import settings

@pytest.mark.skipif(not settings.lang.apis.languagetool.enabled,
                    reason='languagetool disabled')
@pytest.mark.xfail(raises=requests.exceptions.ConnectionError)
def test_languagetool_node():
    # Define the URL of the LanguageTool server
    languagetool_url = settings.lang.apis.languagetool.url

    # Define a text with an intentional error
    text = "This is a test. There are no grammer errors in this sentence."

    # Send a request to the LanguageTool server
    response = requests.post(languagetool_url, data={"text": text, "language": "en-US"})

    # If the response status code is 200, the server is running correctly
    assert response.status_code == 200, f"LanguageTool server is not running. Status code: {response.status_code}"

    # If the response contains matches, the server is functioning correctly
    assert len(response.json().get('matches', [])) > 0, "LanguageTool server is not functioning correctly."
