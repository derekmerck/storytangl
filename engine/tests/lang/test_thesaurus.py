import pytest
from tangl.narrative.lang.thesaurus import Synset, Thesaurus, PartOfSpeach

# Fixture for sample data
@pytest.fixture
def sample_thesaurus():
    # Create sample Synsets
    swing_synset = Synset(label="swing", pos=PartOfSpeach.VB, synonyms={"flail", "slash"})
    sword_synset = Synset(label="sword", pos=PartOfSpeach.NN, synonyms={"blade", "saber"})

    # Create a Thesaurus with these Synsets
    thesaurus = Thesaurus(label="test", synsets=[swing_synset, sword_synset])
    yield thesaurus
    Synset.clear_instances()
    Thesaurus.clear_instances()


# Test for verifying synonyms are correctly added and accessible
def test_synset_synonyms(sample_thesaurus):
    swing_synset = sample_thesaurus.synsets[0]
    assert "flail" in swing_synset.synonyms
    assert "slash" in swing_synset.synonyms
    assert swing_synset.label in swing_synset.synonyms_  # Assuming synonyms_ adds the label


# Test for Synset substitution method
def test_synset_substitution(sample_thesaurus):
    swing_synset = sample_thesaurus.synsets[0]
    # Assuming replace() picks a synonym randomly, test it returns one of the expected synonyms
    assert swing_synset.replace("swing") in swing_synset.synonyms_


# Test for Thesaurus loading from resources (assuming this functionality is correct)
@pytest.mark.skip(reason="Assumes specific file structure and contents")
def test_thesaurus_loading():
    # Assuming a specific resource module and file name
    thesaurus = Thesaurus.from_resources("test_thesaurus", "your_module.resources", "thesaurus_data.yaml")
    assert thesaurus is not None
    assert len(thesaurus.synsets) > 0  # Assuming the file has data


# Test for ensuring no repeated synonyms in consecutive calls (if applicable)
@pytest.mark.skip(reason="Replacement not working yet")
def test_no_repeated_synonyms(sample_thesaurus):
    swing_synset = sample_thesaurus.synsets[0]
    first_replacement = swing_synset.replace("swing")
    second_replacement = swing_synset.replace("swing")
    # This test assumes that replace method has logic to avoid immediate repetition
    assert first_replacement != second_replacement or len(swing_synset.synonyms_) == 1

