from tangl.narrative.voice import Voice

def test_voice_by_id():
    # Custom preprocessing function
    def custom_preprocessor(template_string):
        # Perform any preprocessing actions here. For demo purposes, let's replace "{world}" with "{{universe}}"
        return template_string.replace("<world>", "{{universe}}")

    # Initialize custom environment
    env = Voice(
        strings_map={1: "Hello <world>"},
        string_preprocessors=[custom_preprocessor]
    )

    # Render template
    result = env.from_id(1).render(universe="dog")
    assert result == "Hello dog"
