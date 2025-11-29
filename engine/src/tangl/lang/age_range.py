from typing import Self
from enum import IntEnum

from tangl.utils.enum_plus import EnumPlusMixin

class AgeRange(EnumPlusMixin, IntEnum):
    VERY_YOUNG = CHILD = 1  # 10     ~2^(n+2)?
    YOUNG = TEEN = 2        # 20
    MID = ADULT = 3         # 40
    OLD = 4                 # 80
    VERY_OLD = 5            # 100

    OTHER = -1                                      # use tags to inspect

    @classmethod
    def from_tags(cls, item) -> Self:
        """
        Infer an AgeRange from an entity's tags.

        We interpret tags of the form:
        - "age:<category>"  where <category> matches this enum by name/alias
          (e.g., "age:child", "age:teen", "age:VERY_YOUNG").
        - "age:<n>"         where <n> is a numeric age; these are first
          converted to an AgeRange via `from_age`.
        - Existing AgeRange members present directly in `item.tags`.

        If multiple values are present, we pick the 'oldest' (largest-valued)
        AgeRange, relying on the IntEnum ordering to reflect age.
        """
        if not hasattr(item, "get_tag_kv"):
            return cls.OTHER

        # 1. Direct categorical age-range tags, including enum members.
        ranges = item.get_tag_kv(prefix="age", enum_type=cls)
        if ranges:
            # Choose the "oldest" category: highest numeric value wins.
            return max(ranges, key=lambda r: r.value)

        # 2. Raw numeric ages, to be bucketed into a range.
        ages = item.get_tag_kv(prefix="age", enum_type=int)
        if ages:
            # Use the highest age we saw for bucketing.
            return cls.from_age(max(ages))

        return cls.OTHER

    @classmethod
    def from_age(cls, age: int) -> Self:
        """
        Bucket a numeric age into an AgeRange.

        Assumes that positive-valued members of this IntEnum encode an
        age threshold (in years) and are ordered from youngest to oldest.
        The member with the largest value less than or equal to `age` is
        chosen. Members with negative values (e.g., OTHER) are ignored
        for bucketing.

        This means you can choose either:
        - dense ordinal thresholds (1, 2, 3, 4, 5) that simply encode
          ordering; or
        - meaningful boundaries (e.g., 0, 10, 20, 40, 80) without
          changing this method.

        Examples (with monotonically increasing values):
            age < 0        -> OTHER
            age: 6          -> VERY_YOUNG / CHILD
            age: 15         -> YOUNG / TEEN
            age: 35         -> MID / ADULT
        """
        try:
            age_val = int(age)
        except (TypeError, ValueError):
            return cls.OTHER

        if age_val < 0:
            return cls.OTHER

        # Collect non-negative, non-OTHER candidates and sort by value
        candidates = [
            m for m in cls
            if m is not cls.OTHER and m.value >= 0
        ]
        candidates.sort(key=lambda m: m.value)

        chosen = cls.OTHER
        for bucket in candidates:
            if age_val >= bucket.value:
                chosen = bucket
            else:
                break

        return chosen
