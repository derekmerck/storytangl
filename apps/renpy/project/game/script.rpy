define narrator = Character(None)

default tangl_bridge = None
default tangl_envelope = None
default tangl_choice_id = None
default tangl_characters = {}

init -100 python:
    import os
    import sys
    import sysconfig

    REPO_ROOT = os.path.abspath(os.path.join(config.basedir, "..", "..", ".."))
    os.chdir(REPO_ROOT)
    os.environ.setdefault("TANGL_SERVICE__CACHES__SHELVED", "false")

    if not hasattr(sysconfig, "get_config_var"):
        def _renpy_get_config_var(name):
            if name == "TZPATH":
                return ""
            return None

        sysconfig.get_config_var = _renpy_get_config_var

    if not hasattr(sysconfig, "get_config_vars"):
        def _renpy_get_config_vars(*names):
            if not names:
                return {}
            return {
                name: sysconfig.get_config_var(name)
                for name in names
            }

        sysconfig.get_config_vars = _renpy_get_config_vars

    for relative_path in ("engine/src", "apps/renpy/src"):
        import_path = os.path.join(REPO_ROOT, relative_path)
        if import_path not in sys.path:
            sys.path.insert(0, import_path)

init python:
    from renpy.display.im import Image

    from tangl.renpy import RenPySessionBridge


    def tangl_character_for(line):
        if not line.speaker:
            return narrator

        key = line.speaker_key or line.speaker
        character = tangl_characters.get(key)
        if character is None:
            character = Character(line.speaker)
            tangl_characters[key] = character
        return character


    def tangl_apply_media(op):
        displayable = Image(op.source)
        tag = op.tag or ("tangl_background" if op.action == "scene" else "dialog_im")
        if op.action == "scene":
            renpy.scene()
        renpy.show(tag, what=displayable, tag=tag)


    def tangl_play_turn(turn):
        for op in turn.media_ops:
            tangl_apply_media(op)

        for line in turn.lines:
            tangl_character_for(line)(line.text)

        visible_choices = [choice for choice in turn.choices if choice.available]
        if not visible_choices:
            return None

        return renpy.display_menu(
            [(choice.text, choice.choice_id) for choice in visible_choices]
        )


label start:
    python:
        from tangl.story.fabula.world import World

        World.clear_instances()
        tangl_characters = {}
        tangl_bridge = RenPySessionBridge()
        tangl_envelope = tangl_bridge.start("renpy_demo")
    jump tangl_loop


label tangl_loop:
    python:
        tangl_choice_id = None
        for tangl_turn in tangl_bridge.build_turns(tangl_envelope.fragments):
            tangl_choice_id = tangl_play_turn(tangl_turn)
            if tangl_choice_id is not None:
                break

    if tangl_choice_id is None:
        return

    $ tangl_envelope = tangl_bridge.choose(tangl_choice_id)
    jump tangl_loop
