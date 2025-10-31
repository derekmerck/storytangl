# application layer dispatch:  global > *app* > author > inline
"""
Reference phase handlers for validation, redirects, and journaling.

These handlers provide a minimal end-to-end pipeline suitable for tests and
examples. Real applications can register additional handlers in their domains.
"""
# - the `register` decorator wraps the output in a CallReceipt
# - the phase runner appends the job receipt to the receipt stack in ctx
# - the full call sig currently is `h(cursor: Node, *, ctx: Context)`,
#   be sure to use the correct sig or ignore/consume unnecessary args/kwargs

# Lower layer tasks should never invoke the phase dispatch directly, instead
# add an application layer dispatch like "on_story_planning" that indicates
# task "planning", application layer dispatch will be passed in by the phase
# handler.

from .vm_dispatch import vm_dispatch

from .namespace import on_get_ns, do_get_ns, Namespace
from .validate import on_validate, HasConditions
from .update import on_update, on_finalize, HasEffects
from .redirect import on_prereq, on_postreq
from .journal import on_journal
