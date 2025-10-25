from .pronoun import PoV

from dataclasses import dataclass

# todo: could generate these from pattern

from .helpers.pattern import conjugate as pattern_conjugate

@dataclass
class Conjugates:
    """Standardized nomenclature for verb conjugation tables."""

    infinitive: str = None
    participle: str = None
    progressive: str = None
    _1s: str = None
    _2s: str = None
    _3s: str = None
    _1p: str = None
    _2p: str = None
    _3p: str = None

    source: str = None

    @property
    def gerund(self):
        # "the running man" is a gerund, but "the man is running" is present progressive
        return self.progressive

    @classmethod
    def from_pattern(cls, verb_inf):
        infinitive = verb_inf
        participle = pattern_conjugate(verb_inf, tense="past")
        progressive = pattern_conjugate(verb_inf, aspect="progressive")

        _1s = pattern_conjugate(verb_inf, PoV._1s)
        _2s = pattern_conjugate(verb_inf, PoV._2s)
        _3s = pattern_conjugate(verb_inf, PoV._3s)
        _1p = pattern_conjugate(verb_inf, PoV._1p)
        _2p = pattern_conjugate(verb_inf, PoV._2p)
        _3p = pattern_conjugate(verb_inf, PoV._3p)

        source = "pattern"

        return cls(infinitive, participle, progressive, _1s, _2s, _3s, _1p, _2p, _3p, source)

    def conjugate(self, pov):
        print( self )
        if isinstance(pov, str):
            match pov[0]:
                case "i":
                    attrib = "infinitive"
                case "g":
                    attrib = "progressive"
                case "p":
                    attrib = "participle"
                case _:
                    pov = PoV(pov)
        if isinstance(pov, PoV):
            attrib = pov.name
        res = getattr( self, attrib )
        if pov is PoV._2p and res is None:
            res = self._2s
        return res

    def deconjugate(self, form: str) -> PoV | str:
        for pov in PoV:
            if getattr(self, pov.name) == form:
                return pov
        for name in ['infinitive', 'participle', 'progressive']:
            if getattr(self, name) == form:
                return name
        raise ValueError(f"'{form}' is not a conjugate form of '{self.infinitive}'")
