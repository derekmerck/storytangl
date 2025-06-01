import logging

from tangl.utils.shelved2 import shelved, unshelf
from tangl.config import settings
from tangl.exceptions import RemoteApiUnavailable
from tangl.lang.pronoun import Pronoun
from tangl.lang.conjugates import Conjugates

logger = logging.getLogger(__name__)

class ReversoApi:
    """
    Authoritative lookup for verb conjugation tables using a webpage scraper.

    requires: bs4 (Beautiful Soup)
    """

    query_url = f"https://conjugator.reverso.net/"
    shelf_fn = "reverso2"

    @shelved(fn=shelf_fn)
    @staticmethod
    def get(verb) -> str | bytes:
        import requests

        if not settings.lang.apis.reverso.enabled:
            raise RemoteApiUnavailable( "Reverso API disabled" )

        verb = verb.lower()
        url = ReversoApi.query_url + f"conjugation-english-verb-{verb}.html"
        # reverso blocks requests user-agent  :(
        user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_6_2 rv:3.0; ast-ES) AppleWebKit/535.16.3 (KHTML, like Gecko) Version/4.0 Safari/535.16.3"
        r = requests.get(url, headers={"User-Agent": user_agent})
        if not r.status_code == 200:
            logger.error( "Reverso API error" )
            logger.error( r )
            logger.error( r.content )
            raise requests.RequestException
        return r.content

    @classmethod
    def parse(cls, raw_html) -> dict:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(raw_html, "lxml")

        data = {}
        result_block = soup.find('div', attrs={'class': "result-block-api"} )

        # Get infinitive
        el = result_block.find('div', attrs={'mobile-title': "Infinitive "})
        el = el.find("i", attrs={"class": "verbtxt"})
        data["infinitive"] = "to " + el.text

        # Get gerund
        el = result_block.find('div', attrs={'mobile-title': "Participle Present"})
        el = el.find("i", attrs={"class": "verbtxt"})
        data["gerund"] = el.text

        # Get participle
        el = result_block.find('div', attrs={'mobile-title': "Participle Past"})
        el = el.find("i", attrs={"class": "verbtxt"})
        data["participle"] = el.text

        # Get pronoun cases
        el = result_block.find('p', text="Present")
        rows = el.next_sibling.find_all('li')
        for row in rows:
            pronoun = row.find('i', attrs={'class': "graytxt"})
            conj = row.find('i', attrs={'class': "verbtxt"})
            key = Pronoun.pov_of( str(pronoun.string).strip() ).name
            # key has to be the same as LexRef._normalize_pov
            data[key] = str(conj.string)
        return data

    @classmethod
    def get_conjugates(cls, verb):
        conjug_info = cls.get(verb)
        kwargs = cls.parse(conjug_info)
        return Conjugates(**kwargs, source="reverso")

    @classmethod
    def clear_conjugates(cls, verb):
        unshelf(cls.shelf_fn, verb)
