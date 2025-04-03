import logging

from tangl.utils.shelved2 import shelved, unshelf
from tangl.config import settings
from tangl.exceptions import RemoteApiUnavailable
from tangl.narrative.lang.pronoun import Pronoun
from tangl.narrative.lang.conjugates import Conjugates

logger = logging.getLogger(__name__)

class VerbixApi:
    """
    Authoritative lookup for verb conjugation tables using a webpage scraper.

    requires: bs4 (Beautiful Soup)
    """

    api_key = settings.lang.apis.verbix.token
    query_url = f"https://api.verbix.com/conjugator/iv1/"
    shelf_fn = "verbix2"

    @shelved(fn=shelf_fn)
    @staticmethod
    def get(verb) -> str:
        import requests

        if not settings.lang.apis.verbix.enabled:
            raise RemoteApiUnavailable("Verbix API disabled")
        verb = "to%20" + verb.lower()
        url = VerbixApi.query_url + VerbixApi.api_key + "/1/20/120/" + verb
        r = requests.get(url)
        if not r.status_code == 200:
            logger.error(f"Verbix API error")
            logger.error( r )
            raise requests.RequestException
        return r.content

    @classmethod
    def parse(cls, raw_html) -> dict:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(raw_html, "lxml")

        # print(soup)
        data = {}

        # Get gerund
        el = soup.find( 'b', text="Gerund:")
        el = el.next_sibling
        while not el.text.strip():  # ignore whitespace tags
            el = el.next_sibling
        data["gerund"] = el.text

        # Get participle
        el = soup.find( 'b', text="Participle:")
        el = el.next_sibling
        while not el.text.strip():  # ignore whitespace tags
            el = el.next_sibling
        data["participle"] = el.text

        # Get pronoun cases
        tenses_table = soup.find('table', attrs={'class': '\\"verbtense\\"'})
        rows = tenses_table.find_all('tr')
        # print( rows )
        for row in rows:
            pronoun = row.find('span', attrs={'class': '\\"pronoun\\"'})
            conj = row.find('span', attrs={'class': ['\\"normal\\"', '\\"orto\\"', '\\"irregular\\"']})
            key = Pronoun.pov_of( str(pronoun.string) ).name
            # key has to be the same as LexRef._normalize_pov
            data[key] = str(conj.string)

        return data

    @classmethod
    def get_conjugates(cls, verb):
        conjug_info = cls.get(verb)
        kwargs = cls.parse(conjug_info)
        return Conjugates(**kwargs, source="verbix")

    @classmethod
    def clear_conjugates(cls, verb):
        unshelf(cls.shelf_fn, verb)
