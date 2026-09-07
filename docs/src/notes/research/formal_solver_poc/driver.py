#!/usr/bin/env python3
"""driver.py -- analysis suite for the finishability formalism.

Three queries against engine.lp + world.lp:
  1. MIN-STEP:   smallest horizon h at which the goal is satisfiable,
                 plus the witness plan. UNSAT at every h up to MAX_H is
                 a proof that no path exists within MAX_H moves.
  2. SOFT-LOCK:  for a suspect action, force it into the trace and ask
                 whether the goal is still reachable at ANY horizon.
                 UNSAT everywhere = executing it strands the player.
  3. PROVENANCE: static scan -- which producers exist for each 'known'
                 fact? Facts whose only producer is a trigger are
                 cascade-bound (exist in no market).
"""
import clingo, sys

MAX_H = 20
FILES = ["engine.lp", "world.lp"]

def solve(horizon, extra=""):
    """Ground and solve at a fixed horizon; return plan or None."""
    ctl = clingo.Control([f"-c h={horizon}", "--opt-mode=optN", "0"])
    for f in FILES:
        ctl.load(f)
    if extra:
        ctl.add("base", [], extra)
    ctl.ground([("base", [])])
    best = None
    with ctl.solve(yield_=True) as h:
        for model in h:
            if model.optimality_proven or best is None:
                best = [(str(a.arguments[0]), a.arguments[1].number)
                        for a in model.symbols(shown=True)]
    return sorted(best, key=lambda x: x[1]) if best is not None else None

def min_step():
    print("=" * 64)
    print("QUERY 1: minimum steps to the summit")
    print("=" * 64)
    for h in range(1, MAX_H + 1):
        plan = solve(h)
        if plan is not None:
            n_player = sum(1 for a, _ in plan if not a.startswith(
                ("reveal_", "evict_", "partner_appears")))
            print(f"first satisfiable horizon: {h}  "
                  f"({n_player} player moves, {len(plan)-n_player} forced)\n")
            for a, t in plan:
                forced = a in ("reveal_mom", "evict_gwen", "partner_appears")
                print(f"  t={t:2d}  {'[FATE]  ' if forced else '[player]'} {a}")
            return
        print(f"  h={h:2d}: UNSAT (no plan exists within {h} moves)")
    print(f"NO PATH EXISTS within {MAX_H} moves.")

def soft_lock(action):
    print("\n" + "=" * 64)
    print(f"QUERY 2: soft-lock check -- is '{action}' ever fatal?")
    print("=" * 64)
    force = f":- not forced_once. forced_once :- occurs({action}, T)."
    for h in range(1, MAX_H + 1):
        if solve(h, extra=force) is not None:
            print(f"  survivable: goal reachable at h={h} even after {action}.")
            return
    print(f"  SOFT-LOCK PROVEN: if the player ever executes '{action}',")
    print(f"  the summit is unreachable at every horizon up to {MAX_H}.")

def provenance():
    print("\n" + "=" * 64)
    print("QUERY 3: provenance -- which people are cascade-bound?")
    print("=" * 64)
    prog = """
      producer(P, A) :- add(A, state(P, known)).
      market_producer(P)  :- producer(P, A), not trigger(A).
      cascade_bound(P)    :- producer(P, _), not market_producer(P).
      seeded(P)           :- init(state(P, known)).
      #show cascade_bound/1. #show seeded/1.
    """
    ctl = clingo.Control()
    ctl.load("world.lp")
    ctl.add("base", [], prog)
    ctl.ground([("base", [])])
    with ctl.solve(yield_=True) as h:
        for m in h:
            for s in sorted(m.symbols(shown=True), key=str):
                tag = ("exists ONLY as a consequence -- no market producer"
                       if s.name == "cascade_bound" else "part of the seed")
                print(f"  {str(s.arguments[0]):10s} {tag}")

if __name__ == "__main__":
    min_step()
    soft_lock("eat_icecream")
    provenance()

def chekhov():
    print("\n" + "=" * 64)
    print("QUERY 4: Chekhov's law -- def-use analysis of the rulebase")
    print("=" * 64)
    prog = """
      offered(F)  :- add(_, F).
      offered(F)  :- init(F).
      consumed(F) :- pre(_, F).
      consumed(F) :- goal(F).
      %% forward: every offer needs a consumer (warning-class)
      unfired_gun(F) :- offered(F), not consumed(F), not red_herring(F).
      %% backward: every consumer needs a satisfier (error-class)
      unsatisfiable(F) :- consumed(F), not offered(F).
      #show unfired_gun/1. #show unsatisfiable/1.
    """
    ctl = clingo.Control()
    ctl.load("world.lp")
    ctl.add("base", [], prog)
    ctl.ground([("base", [])])
    found = False
    with ctl.solve(yield_=True) as h:
        for m in h:
            for s in sorted(m.symbols(shown=True), key=str):
                found = True
                sev = ("ERROR: no producer anywhere"
                       if s.name == "unsatisfiable"
                       else "warning: offered, never consumed")
                print(f"  {str(s.arguments[0]):28s} {sev}")
    if not found:
        print("  clean: every gun fires, every need is satisfiable.")

if __name__ == "__main__":
    chekhov()
