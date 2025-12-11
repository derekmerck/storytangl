from uuid import uuid4

from tangl.vm36.execution.phases import Phase, PhaseBus
from tangl.vm36.execution.tick import StepContext

def test_build_phase_bus():

    def build():
        bus = PhaseBus()

        # VALIDATE (pure reads, raise or no-op if invalid)
        def validate(c: "StepContext"):
            # You can compute Facts on demand
            # (import Graph if you want to examine it here; omitted for brevity)
            pass

        bus.register(Phase.VALIDATE, "guards", 50, validate)

        # EXECUTE (emit effects only)
        def exec_handlers(c: "StepContext"):
            hero = c.create_node("tangl.core36.entity:Node", label="hero", tags={"player"})
            room = c.create_node("tangl.core36.entity:Node", label="room", tags={"place"})
            c.add_edge(hero, room, "at")

        bus.register(Phase.EXECUTE, "spawn", 50, exec_handlers)

        # JOURNAL (emit fragments)
        def journal(c: "StepContext"):
            c.say({"type": "text", "text": "A hero appears in the room."})

        bus.register(Phase.JOURNAL, "narrate", 50, journal)

        return bus

    bus = build()

    ctx = StepContext(story_id=uuid4(), epoch=0, choice_id="c2", base_hash=0)
    # Run phases
    bus.run(Phase.VALIDATE, ctx)
    bus.run(Phase.EXECUTE, ctx)
    ctx._handler = None  # defensive reset (bus already does this)
    bus.run(Phase.JOURNAL, ctx)
