from pprint import pprint
import logging

import requests

from tangl.utils.shelved2 import shelved
from tangl.exceptions import RemoteApiUnavailable
from tangl.config import settings

logger = logging.getLogger(__name__)


class MeriamWebsterApi:
    """
    Can query collegiate dict or thesaurus
    """

    api_keys = { 'collegiate': settings.lang.apis.meriamwebster.collegiate_token,
                 'thesaurus': settings.lang.apis.meriamwebster.thesaurus_token  }

    query_url = "https://dictionaryapi.com/api/v3/references/"
    shelf_fn = "mw2"

    @shelved(fn=shelf_fn)
    @staticmethod
    def get(word, ref) -> dict:

        if not settings.lang.apis.meriamwebster.enabled:
            raise RemoteApiUnavailable( "MW API disabled" )

        word = word.lower()
        url = MeriamWebsterApi.query_url + f"{ref}/json/{word}"
        r = requests.get( url, params={'key': MeriamWebsterApi.api_keys[ref]})
        if not r.status_code == 200:
            logger.error(f"MW API error")
            logger.error( url )
            logger.error( r.request )
            logger.error( r )
            raise requests.RequestException
        return r.json()

    @classmethod
    def distill_synonyms(self, data):

        res = []
        try:
            for i in data[0]['def'][0]['sseq']:
                data_ = i[0][1]
                data0 = []
                if 'syn_list' in data_:
                    data0 = data_['syn_list']
                elif 'sim_list' in data_:
                    data0 = data_['sim_list']
                for item in data0:
                    res += [ x['wd'] for x in item ]
        except KeyError:
            pprint( data )
            raise
        return res

    @classmethod
    def get_synonyms(cls, word):
        data = cls.get( word, "thesaurus" )
        res = cls.distill_synonyms( data )
        return res

