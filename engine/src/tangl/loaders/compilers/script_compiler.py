from __future__ import annotations

class ScriptCompiler:
    """Deprecated runtime37 script compiler bridge.

    Runtime37 script-manager compilation was retired during v38 namespace cutover.
    World loading now uses codec decoding + ``StoryCompiler`` directly.
    """

    def compile(self, script_data: dict):
        _ = script_data
        raise RuntimeError(
            "ScriptCompiler.compile() is no longer supported; "
            "runtime37 script-manager loading was retired."
        )
