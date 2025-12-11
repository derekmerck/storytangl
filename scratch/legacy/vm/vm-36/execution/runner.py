# tangl/vm/runner.py
from dataclasses import dataclass
from typing import Callable, Optional
from uuid import UUID
from tangl.vm36.scoping import Scope
from .session import GraphSession
from .phases import PhaseBus
from .tick import StepContext
from .patch import PatchBuffer

@dataclass
class RunConfig:
    max_steps: int = 64
    collapse_super_patch: bool = False

@dataclass
class RunResult:
    steps: int
    stopped: str            # "blocked" | "no_choice" | "loop" | "max_steps"
    patches: list           # list[Patch]
    super_patch: Optional[object] = None

# User supplies a chooser that decides the next "choice" (or redirect) given the session.
Chooser = Callable[[GraphSession], Optional[Callable[[StepContext, PhaseBus], None]]]

def run_until_blocked(sess: GraphSession, bus: PhaseBus, choose: Chooser, cfg: RunConfig) -> RunResult:
    buf = PatchBuffer()
    seen: set[tuple[UUID, ...]] = set()
    steps = 0

    while steps < cfg.max_steps:
        # assemble base scope at current cursor
        ctx = StepContext(
            story_id=sess.graph_id, epoch=sess.version,
            choice_id=f"auto:{steps}", base_hash=0, graph=sess.graph
        )
        if sess.cursor_uid and sess.domains:
            facts = ctx.facts
            scope = Scope.assemble(sess.graph, facts, sess.cursor_uid, domains=sess.domains)
            cur = sess.graph.get(sess.cursor_uid); label = getattr(cur, "label", None) if cur else None
            ctx.mount_scope(scope.ns, scope.handlers_by_phase,
                            active_domains=scope.active_domains,
                            cursor_uid=sess.cursor_uid, cursor_label=label)

        # VALIDATE/EXECUTE/JOURNAL for this tick driven by chooser
        build = choose(sess)
        if build is None:
            return _finish(buf, steps, "no_choice", cfg)

        # Let the chooser fill the bus and run phases however it likes.
        # Minimal default: just call the provided callable with (ctx, bus)
        build(ctx, bus)

        p = sess.run_tick(choice_id=f"auto:{steps}", build=lambda _: None)  # we already executed via build
        buf.add(p); steps += 1

        # loop detection: simple frontier signature (cursor only), extend as needed (stack, enabled choices)
        sig = (sess.cursor_uid,)
        if sig in seen:
            return _finish(buf, steps, "loop", cfg)
        seen.add(sig)

        # chooser can auto-redirect by setting sess.cursor_uid in POST commit; if no redirect, we’re blocked
        nxt = choose(sess)
        if nxt is None:
            return _finish(buf, steps, "blocked", cfg)

    return _finish(buf, steps, "max_steps", cfg)

def _finish(buf: PatchBuffer, steps: int, why: str, cfg: RunConfig) -> RunResult:
    sp = buf.to_super_patch() if cfg.collapse_super_patch else None
    return RunResult(steps=steps, stopped=why, patches=buf.patches, super_patch=sp)
