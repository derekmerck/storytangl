from abc import ABC
from enum import Enum

class EnumReferent( ABC ):
    """
    Simple referent pattern where qualifiers are enumerated with their conditions
    """

    # Inherit this in the derived class
    class Qualifier(Enum):
        # QUAL = "name", lambda self: return True
        @classmethod
        def _missing_(cls, value):
            for k, v in cls.__members__.items():
                if value == v.value[0]:
                    return v

    @property
    def qualifiers(self) -> set:
        # simple approach pre-computes all the values
        return set( [ q for q in self.Qualifier if q.value[1](self) ] )

    def naive_qualified_by(self, qual: str | Qualifier):
        """This restricts dependencies in evaluations b/c all possible
        qualifiers are determined at once, but the qualifiers prop could
        be useful."""
        try:
            qual = self.Qualifier( qual )
            return qual in self.qualifiers
        except ValueError as e:
            print(e)

    def qualified_by(self, qual: str | Qualifier):
        try:
            qual = self.Qualifier(qual)
            return qual.value[1](self)
        except ValueError as e:
            print(e)
