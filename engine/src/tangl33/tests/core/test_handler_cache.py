from tangl33.core import Capability, HandlerCache, Phase, Tier, Service

# ---------------------------------------------------------------------------
# Helpers: lightweight dummy Capability for testing
# ---------------------------------------------------------------------------
def make_cap(priority: int, phase: Phase = Phase.GATHER,
             tier: Tier = Tier.NODE) -> Capability:
    class DummyCap(Capability):
        def apply(self, *a, **kw):  # pragma: no cover
            pass
    return DummyCap(phase=phase, tier=tier, service=Service.CONTEXT, priority=priority)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
def test_register_and_iter_basic():
    cache = HandlerCache()
    cap = make_cap(priority=0)
    cache.register(cap)

    caps = list(cache.iter_phase(cap.phase, cap.tier))
    assert caps == [cap]


def test_priority_sort_descending():
    cache = HandlerCache()
    low = make_cap(priority=0)
    mid = make_cap(priority=5)
    high = make_cap(priority=10)

    for c in (low, high, mid):   # register unsorted
        cache.register(c)

    caps = list(cache.iter_phase(low.phase, low.tier))
    assert caps == [high, mid, low], "Capabilities should sort by -priority"


def test_phase_tier_isolation():
    cache = HandlerCache()
    a = make_cap(priority=1, phase=Phase.GATHER, tier=Tier.NODE)
    b = make_cap(priority=1, phase=Phase.RENDER, tier=Tier.NODE)
    c = make_cap(priority=1, phase=Phase.GATHER, tier=Tier.GRAPH)

    for cap in (a, b, c):
        cache.register(cap)

    # Only 'a' matches its exact (phase, tier)
    assert list(cache.iter_phase(Phase.GATHER, Tier.NODE)) == [a]
    # Empty when nothing registered
    assert list(cache.iter_phase(Phase.RESOLVE, Tier.DOMAIN)) == []
