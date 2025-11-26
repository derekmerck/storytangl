import pytest

from tangl.media.media_creators.tts_forge.eleven_api import ElevenLabsApi
from tangl.config import settings
from tangl.exceptions import RemoteApiUnavailable

try:
    HAS_ELEVEN_API = settings.media.apis.elevenlabs.enabled
    print( settings.content.apis.elevenlabs.token )
except AttributeError:
    HAS_ELEVEN_API = False

ELEVEN_VOICE_ID = "default"

@pytest.mark.skipif(not HAS_ELEVEN_API, reason="api disabled")
def test_elevenlabs():
    print("Checking ElevenLabs availability and api")
    api = ElevenLabsApi()
    user_info = api.get_user_info()
    if user_info.get("detail", {}).get('status') == "invalid_api_key":
        raise RemoteApiUnavailable

    from pprint import pprint
    pprint( api.voice_ids )
    assert ELEVEN_VOICE_ID in api.voice_ids
    assert api.quota_remaining
    print( "quota: ", api.quota_remaining )

    try:
        if settings.testing.use_elevenlabs_quota:
            api.get_audio(ELEVEN_VOICE_ID,
                          "Pad kid poured curd pulled cod.",
                          "tmp_voice_test.mp3")
            print("synthesized test string")
    except KeyError:
        pass
