
from tangl.core.services import Satisfiable
from tangl.core.services.service_ctx import _PRED_SVC, _CTX_SVC, service_ctx

def test_service_ctx() -> None:

    always_true_pred = lambda ent, ctx: True
    dummy_ctx        = lambda ent: {"dummy": True}

    ent = Satisfiable(locals={'foo': 'bar'})

    assert ent.gather_context()['foo'] == 'bar', "Normal behavior with standard services"

    with service_ctx({_PRED_SVC: always_true_pred, _CTX_SVC: dummy_ctx}):

        print( ent.gather_context() )
        assert ent.gather_context() == { 'dummy': True }, "Override services replace standard service"
        assert ent.is_satisfied()

        token = _PRED_SVC.set( lambda ent, ctx: False )
        assert not ent.is_satisfied(), "Double override"
        _PRED_SVC.reset(token)

        assert ent.is_satisfied(), "Back to override behavior"

    assert ent.gather_context()['foo'] == 'bar', "Back to normal behavior"
