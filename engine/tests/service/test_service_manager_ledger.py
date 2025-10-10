from uuid import uuid4

import pytest

from tangl.persistence import LedgerEnvelope, PersistenceManagerFactory
from tangl.service import ServiceManager


@pytest.fixture
def service_manager_with_persistence(tmp_path):
    manager = PersistenceManagerFactory.create_persistence_manager(
        manager_name="pickle_file",
        user_data_path=tmp_path,
    )
    return ServiceManager(persistence_manager=manager)


def test_create_and_open_ledger(service_manager_with_persistence):
    service_manager = service_manager_with_persistence

    ledger_id = service_manager.create_ledger()

    with service_manager.open_ledger(user_id=uuid4(), ledger_id=ledger_id) as ledger:
        assert ledger.uid == ledger_id
        assert ledger.step == 0
        assert ledger.graph.find_one(label="start") is not None


def test_ledger_mutation_persists(service_manager_with_persistence):
    service_manager = service_manager_with_persistence
    ledger_id = service_manager.create_ledger()

    with service_manager.open_ledger(user_id=uuid4(), ledger_id=ledger_id, write_back=True) as ledger:
        ledger.step = 99

    with service_manager.open_ledger(user_id=uuid4(), ledger_id=ledger_id) as ledger:
        assert ledger.step == 99


def test_ledger_no_spurious_write(service_manager_with_persistence):
    service_manager = service_manager_with_persistence
    ledger_id = service_manager.create_ledger()

    initial_envelope = LedgerEnvelope.model_validate(
        service_manager.persistence_manager.get(ledger_id)
    ).model_dump()

    with service_manager.open_ledger(user_id=uuid4(), ledger_id=ledger_id, write_back=True):
        pass

    final_envelope = LedgerEnvelope.model_validate(
        service_manager.persistence_manager.get(ledger_id)
    ).model_dump()

    assert final_envelope == initial_envelope
