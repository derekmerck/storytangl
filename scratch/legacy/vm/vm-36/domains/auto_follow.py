# tangl/domains/auto_follow.py
from tangl.vm36.execution.session import GraphSession
from tangl.vm36.execution.tick import StepContext
from tangl.vm36.execution.phases import Phase

def auto_follow_chooser(sess: GraphSession):
    """
    Return a callable (ctx, bus) that will:
      - VALIDATE (guards)
      - EXECUTE one auto transition if there is exactly one
      - JOURNAL minimally (optional)
    Return None when multiple choices or none are available (blocked/user input).
    """
    # todo: this is just an example, in general, we don't always want to follow single
    #       choices, those still may require user input/agreement; we want to follow
    #       any unguarded transition marked "auto-follow" or something like that.
    def _build(ctx: StepContext, bus):
        # 1) VALIDATE global + scope guards already on bus
        bus.run(Phase.VALIDATE, ctx)

        # 2) Decide auto transition (user supplies how to enumerate choices)
        choices = enumerate_enabled_choices(sess, ctx)   # your function
        if len(choices) != 1:
            # signal “blocked”: the runner will stop after this tick
            return

        # 3) EXECUTE the single choice
        choices[0].handler(ctx)                         # emits effects, can set_next_cursor

        # 4) (optional) JOURNAL auto-follow narration
        bus.run(Phase.JOURNAL, ctx)

    # If there isn’t exactly one choice *now*, tell runner to stop
    probe = enumerate_enabled_choices(sess, None)
    return _build if len(probe) == 1 else None