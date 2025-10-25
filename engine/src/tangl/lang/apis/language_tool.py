import logging

import requests

from tangl.config import settings
from tangl.exceptions import RemoteApiUnavailable

logger = logging.getLogger(__name__)

class LanguageToolApi:
    """
    $ brew install languagetool
    $ /opt/homebrew/opt/languagetool/bin/languagetool-server --port 8081 --allow-origin
    """
    query_url = settings.lang.apis.languagetool.url

    @classmethod
    def check(cls, text: str, disabled_rules: list = None, **kwargs):

        if not settings.lang.apis.languagetool.enabled:
            raise RemoteApiUnavailable( "LanguageTool API disabled" )

        url = LanguageToolApi.query_url + "/check"
        data = {"text": text, "language": "en-US"}
        if disabled_rules:
            data['disabledRules'] = ",".join(disabled_rules)
        try:
            r = requests.post(url, data=data)
            return r.json().get('matches')
        except requests.exceptions.ConnectTimeout:  # pragma: no cover
            raise RemoteApiUnavailable
        except:   # pragma: no cover
            logger.error(f"LanguageTool API error")
            logger.error(url)
            logger.error(r.text)
            logger.error(r.content)
            logger.error(r.request.body)
            raise
