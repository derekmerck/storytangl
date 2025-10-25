# mlconjug3 handlers

import warnings
warnings.filterwarnings(action='ignore', category=UserWarning)

DeprecationWarning("MlConjug3 is not particularly reliable compared to `pattern`.")

from tangl.utils.shelved2 import shelved, unshelf
from tangl.lang.conjugates import Conjugates

try:
    import mlconjug3
    HAS_MLCONJUG = True
except ImportError:
    mlconjug3 = object
    HAS_MLCONJUG = False

class Mlc3Api:
    """
    Non-authoritative lookup for verb conjugation tables

    requires: mlconjug3
    (appears to conflict with pyyaml ^6.0.1 dep?)
    """

    shelf_fn = "conj2"

    @shelved(fn=shelf_fn)
    @staticmethod
    def get(verb):
        if not HAS_MLCONJUG:
            raise ImportError("Install mlconjug3 to use this handler")
        default_conjugator = mlconjug3.Conjugator(language='en')
        return default_conjugator.conjugate(verb).conjug_info

    @classmethod
    def parse(cls, conjug_info):
        kwargs = {
            'infinitive': conjug_info['infinitive']['infinitive present'],
            'participle': conjug_info['indicative']['indicative past tense']['3p'],
            'gerund': conjug_info['indicative']['indicative present continuous']['3p'],
        }
        kwargs |= {f'_{k}': v for k, v in conjug_info['indicative']['indicative present'].items()}
        return kwargs

    @classmethod
    def get_conjugates(cls, verb):
        conjug_info = cls.get(verb)
        kwargs = cls.parse(conjug_info)
        return Conjugates(**kwargs, source="mlconjug3")

    @classmethod
    def clear_conjugates(cls, verb):
        unshelf(cls.shelf_fn, verb)
