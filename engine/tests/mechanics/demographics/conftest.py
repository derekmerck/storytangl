import pytest

from tangl.mechanics.demographics.data_models import Country, NameBank, Region, Subtype

def has_real_demographic_data() -> bool:
    """Check if real demographic data was successfully loaded."""
    country_count = sum(1 for _ in Country.all_instances())
    namebank_count = sum(1 for _ in NameBank.all_instances())
    # If we have more than a handful of countries and namebanks, the real data loaded
    return country_count > 5 and namebank_count > 5


# Marker for tests requiring real LFS data
requires_real_data = pytest.mark.skipif(
    not has_real_demographic_data(),
    reason="Real demographic data not available (LFS not pulled or data failed to load)",
)


@pytest.fixture(scope="session", autouse=True)
def ensure_minimal_demographic_data():
    """Ensure minimal demographic data exists for mechanics testing.

    If real data loaded (LFS available), use that. If not, populate minimal stub data so
    the mechanics tests can run.
    """
    if has_real_demographic_data():
        # Real data is present, don't interfere
        yield
        return

    # No real data - populate minimal stubs for mechanics testing
    _populate_stub_data()
    yield
    # Don't clear - other tests may need it


def _populate_stub_data() -> None:
    """Create minimal but realistic demographic data for testing mechanics."""
    # Only populate if not already done
    if any(True for _ in Country.all_instances()):
        return

    # Create minimal structure
    european = Subtype(label="european", name="European", demonym="European")
    asian = Subtype(label="asian", name="Asian", demonym="Asian")

    europe = Region(
        label="europe",
        name="Europe",
        demonym="European",
        eth_mix={"european": 1},
    )
    asia = Region(
        label="asia",
        name="Asia",
        demonym="Asian",
        eth_mix={"asian": 1},
    )

    # Create test countries with labels that match real data
    fra = Country(label="fra", name="France", demonym="French", population=67_000_000)
    deu = Country(label="deu", name="Germany", demonym="German", population=83_000_000)
    jpn = Country(label="jpn", name="Japan", demonym="Japanese", population=126_000_000)

    europe.countries.add(fra)
    europe.countries.add(deu)
    asia.countries.add(jpn)

    # Create name banks
    NameBank(
        label="fra",
        female=["Marie", "Sophie", "Claire"],
        male=["Jean", "Pierre", "Luc"],
        surname=["Dupont", "Durand", "Martin"],
    )
    NameBank(
        label="deu",
        female=["Anna", "Maria", "Lisa"],
        male=["Hans", "Klaus", "Fritz"],
        surname=["Mueller", "Schmidt", "Wagner"],
    )
    NameBank(
        label="jpn",
        female=["Yuki", "Aiko", "Sakura"],
        male=["Hiroshi", "Takeshi", "Kenji"],
        surname=["Tanaka", "Sato", "Suzuki"],
    )
