import pytest

from tangl.lang.body_parts import BodyRegion, BodyPart
from tangl.core.entity import Entity


class DummyEntity(Entity):
    """Minimal concrete entity for tag-based tests."""
    pass


def make_entity(tags) -> DummyEntity:
    # Assumes Entity accepts `tags` in its constructor, as in other tests.
    return DummyEntity(tags=set(tags))


# --- BodyRegion.to_part_mask -------------------------------------------------

def test_bodyregion_to_part_mask_basic_composites():
    """
    BodyRegion.to_part_mask should map each coarse region to the corresponding
    composite BodyPart alias with the same name.
    """
    assert BodyRegion.HEAD.to_part_mask() == BodyPart.HEAD
    assert BodyRegion.TOP.to_part_mask() == BodyPart.TOP
    assert BodyRegion.BOTTOM.to_part_mask() == BodyPart.BOTTOM

    assert BodyRegion.ARMS.to_part_mask() == BodyPart.ARMS
    assert BodyRegion.HANDS.to_part_mask() == BodyPart.HANDS
    assert BodyRegion.LEGS.to_part_mask() == BodyPart.LEGS
    assert BodyRegion.FEET.to_part_mask() == BodyPart.FEET


# --- BodyPart.to_regions -----------------------------------------------------

def test_bodypart_to_regions_left_hand_memberships():
    """
    LEFT_HAND should overlap the HANDS region and the TOP region, but not ARMS.
    """
    regions = BodyPart.LEFT_HAND.to_regions()

    assert BodyRegion.HANDS in regions
    assert BodyRegion.TOP in regions
    assert BodyRegion.ARMS not in regions
    assert BodyRegion.BOTTOM not in regions
    assert BodyRegion.HEAD not in regions


def test_bodypart_to_regions_anywhere_hits_all_coarse_regions():
    """
    ANYWHERE is defined as HEAD | TOP | BOTTOM, so it should report all three.
    """
    regions = BodyPart.ANYWHERE.to_regions()

    assert regions.issuperset(
        {BodyRegion.HEAD, BodyRegion.TOP, BodyRegion.BOTTOM}
    )


def test_bodyregion_roundtrip_contains_original_region():
    """
    For each BodyRegion, region.to_part_mask().to_regions() should at least
    include the original region (it may include additional overlapping regions,
    e.g. ARMS is a subset of TOP).
    """
    for region in BodyRegion:
        part_mask = region.to_part_mask()
        roundtrip_regions = part_mask.to_regions()
        assert region in roundtrip_regions


# --- BodyPart.from_tags ------------------------------------------------------

def test_bodypart_from_tags_with_part_prefix():
    """
    part:<name> tags should be parsed directly to BodyPart values.
    """
    e = make_entity({"part:left_hand"})

    mask = BodyPart.from_tags(e)

    assert mask is not None
    assert mask & BodyPart.LEFT_HAND == BodyPart.LEFT_HAND
    # No legs in this mask
    assert mask & BodyPart.LEGS == BodyPart.NONE

def test_bodypart_from_tags_with_region_prefix():
    """
    region:<name> tags should also be converted to BodyPart composites.
    """
    e = make_entity({"region:hands"})

    mask = BodyPart.from_tags(e)

    assert mask is not None
    # Should include both hands
    assert mask & BodyPart.HANDS == BodyPart.HANDS
    # But not legs
    assert mask & BodyPart.LEGS == BodyPart.NONE

def test_bodyregion_bodypart_casting():

    top_r = BodyRegion.TOP
    top_p = BodyPart.TOP

    assert BodyPart( top_r ) is top_p


def test_bodypart_from_tags_with_region_enum_instance():
    """
    If tags contain BodyRegion enum members directly, they should be converted
    to the corresponding BodyPart composites via EnumPlus casting.
    """
    e = make_entity({BodyRegion.TOP})

    mask = BodyPart.from_tags(e)

    assert mask is not None
    assert mask & BodyPart.TOP == BodyPart.TOP
    # TOP should not include any BOTTOM-only parts
    assert mask & BodyPart.BOTTOM == BodyPart.NONE


def test_bodypart_from_tags_no_relevant_tags_returns_none():
    """
    When there are no part:/region: tags and no BodyRegion/BodyPart tags,
    we should get None.
    """
    e = make_entity({"foo:bar", "other:thing"})

    mask = BodyPart.from_tags(e)

    assert mask is None


# --- BodyPart subtraction ----------------------------------------------------

def test_bodypart_subtraction_top_minus_arms():
    """
    BodyPart subtraction is bitmask subtraction: TOP - ARMS removes arms but
    leaves torso and hands intact.
    """
    top_minus_arms = BodyPart.TOP - BodyPart.ARMS

    # Should not include any ARM bits
    assert top_minus_arms & BodyPart.ARMS == BodyPart.NONE

    # Should still include torso
    assert top_minus_arms & BodyPart.TORSO == BodyPart.TORSO

    # ARMS excludes hands, so hands should still be present in TOP - ARMS
    assert top_minus_arms & BodyPart.HANDS == BodyPart.HANDS
