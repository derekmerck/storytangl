import pytest
from tangl.mechanics.credentials.enums import Region, Indication, RestrictionLevel

@pytest.mark.skip(reason="doesn't work like this anymore")
def test_regional_restriction_map():
    test_map = RegionalRestrictionMap(
        {
            Region.LOCAL: {
                Indication.TRAVEL: RestrictionLevel.ALLOWED,
                Indication.WORK: RestrictionLevel.FORBIDDEN
            },
            Region.FOREIGN_EAST: {
                Indication.TRAVEL: RestrictionLevel.WITH_PERMIT,
                Indication.WORK: RestrictionLevel.ALLOWED
            }
        },
        blacklist=["bad_candidate"],
        whitelist=["good_candidate"]
    )

    # Test if the map was created with the right values
    assert test_map[Region.LOCAL][Indication.TRAVEL] == RestrictionLevel.ALLOWED
    assert test_map[Region.FOREIGN_EAST][Indication.WORK] == RestrictionLevel.ALLOWED

    # Test if blacklist and whitelist are correct
    assert "bad_candidate" in test_map.blacklist
    assert "good_candidate" in test_map.whitelist

    # Test if adding new restrictions work
    test_map[Region.FOREIGN_WEST] = {
        Indication.TRAVEL: RestrictionLevel.WITH_ANON,
        Indication.WORK: RestrictionLevel.WITH_ID
    }
    assert test_map[Region.FOREIGN_WEST][Indication.TRAVEL] == RestrictionLevel.WITH_ANON
    assert test_map[Region.FOREIGN_WEST][Indication.WORK] == RestrictionLevel.WITH_ID
