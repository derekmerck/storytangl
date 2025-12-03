import pytest

@pytest.mark.xfail(reason="Example of a MVP integration test")
def test_complete_story_flow():
    """Test a complete story from setup through multiple choices."""
    # Setup
    sess = create_test_session()
    sess.graph = create_tavern_scene()

    # Discovery
    choices = discover_choices(sess)
    assert "talk_to_innkeeper" in [c.id for c in choices]

    # Execute choice
    execute_choice(sess, "talk_to_innkeeper")

    # Verify journal
    assert "The innkeeper greets you" in get_journal_text(sess)

    # Verify graph evolution
    assert sess.graph.find_one(label="innkeeper_dialogue")