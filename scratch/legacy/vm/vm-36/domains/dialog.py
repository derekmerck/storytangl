from tangl.vm36.execution.phases import Phase
from tangl.vm36.execution.tick import StepContext

class DialogueDomain:
    def vars(self, g, node):
        return {"say": lambda text: {"type":"text","text": f'{node.label}: {text}'}}
    def handlers(self, g, node):
        # Mount a JOURNAL handler that uses the var
        def journal(ctx: StepContext):
            make = ctx.ns["say"]
            ctx.say(make("hello"))
        return [(Phase.JOURNAL, "dialogue.say.hello", 50, journal)]
