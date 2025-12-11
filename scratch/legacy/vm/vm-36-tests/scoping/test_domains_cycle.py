import pytest
from tangl.vm36.scoping.domains import DomainRegistry

def test_domain_registry_cycle_detection():
    d = DomainRegistry()
    d.add("A", parents=("B",), provider=object())
    d.add("B", parents=("A",), provider=object())
    with pytest.raises(ValueError):
        d.linearize(["A"])