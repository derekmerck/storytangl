from tangl.vm.dispatch.materialize_task import MaterializePhase, MaterializeTask


def test_materialize_task_enum_values():
    assert MaterializeTask.MATERIALIZE == "fabula.materialize"


def test_materialize_phase_ordering():
    assert MaterializePhase.EARLY < MaterializePhase.NORMAL
    assert MaterializePhase.NORMAL < MaterializePhase.LATE
    assert MaterializePhase.LATE < MaterializePhase.LAST


def test_materialize_phase_values():
    assert MaterializePhase.EARLY == 10
    assert MaterializePhase.NORMAL == 50
    assert MaterializePhase.LATE == 80
    assert MaterializePhase.LAST == 90
