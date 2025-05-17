from enum import Enum

class VisitPhase(Enum):
    GATHER = 10            # discover scopes, assemble scoped svc view, ctx, tmplx
    FIRST = 20             # enter handlers
    RESOLVE = 30           # find or provide handlers, ctx, tmplx -> find, link, or add nodes on the graph
    REDIRECT = 40          # choice handlers(BEFORE) -> follow un-gated choices
    APPLY_EFFECTS = 50     # effects handlers(BEFORE) -> apply (un-gated?) effects
    UPDATE_JOURNAL = 60    # render handlers -> to generate content, addend to journal
    BOOK_KEEPING = 80      # effects handlers (AFTER) -> apply (un-gated?) effects
    LAST = 90              # finalize handlers
    CONTINUES = 100        # choice handlers (AFTER) -> follow up-gated choices
    BLOCK = 110            # wait on user input if at least one manual choice is available

