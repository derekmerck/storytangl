from uuid import uuid4
from tempfile import TemporaryDirectory
from pathlib import Path

from tangl.persist.sqlite_repo import SQLiteRepo
from tangl.vm36.execution.session import GraphSession
from tangl.vm36.execution.phases import Phase, PhaseBus
from tangl.vm36.execution.patch import resolve_fqn

def resolver(fqn: str):
    return resolve_fqn(fqn)

def test_sqlite_repo_persist_and_reload():
    with TemporaryDirectory() as td:
        db = Path(td, "eventlog.sqlite")
        repo = SQLiteRepo(str(db))

        gid = uuid4()
        sess = GraphSession(graph_id=gid, repo=repo)
        sess.load_or_init(resolver)

        def build(ctx):
            bus = PhaseBus()
            def exec_(c):
                a = c.create_node("tangl.core36.entity:Node", label="A")
                b = c.create_node("tangl.core36.entity:Node", label="B")
                c.add_edge(a, b, "link")
            bus.register(Phase.EXECUTE, "spawn", 50, exec_)
            bus.run(Phase.EXECUTE, ctx)
        sess.run_tick(choice_id="first", build=build)

        # New session (fresh object), load from snapshot (none yet) + events (we're not replaying here, just checking snapshot saving on next tick)
        # Force a snapshot by setting snapshot_every=1 for the next session (or run another tick to trigger