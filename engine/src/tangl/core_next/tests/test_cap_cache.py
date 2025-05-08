from tangl.core_next import Capability, CapabilityCache, StepPhase, Tier

# ---------------------------------------------------------------------------
# Helpers: lightweight dummy Capability for testing
# ---------------------------------------------------------------------------
def make_cap(priority: int, phase: StepPhase = StepPhase.GATHER_CONTEXT,
             tier: Tier = Tier.NODE) -> Capability:
    class DummyCap(Capability):
        def apply(self, *a, **kw):  # pragma: no cover
            pass
    return DummyCap(phase=phase, tier=tier, priority=priority)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
def test_register_and_iter_basic():
    cache = CapabilityCache()
    cap = make_cap(priority=0)
    cache.register(cap)

    caps = list(cache.iter_phase(cap.phase, cap.tier))
    assert caps == [cap]


def test_priority_sort_descending():
    cache = CapabilityCache()
    low = make_cap(priority=0)
    mid = make_cap(priority=5)
    high = make_cap(priority=10)

    for c in (low, high, mid):   # register unsorted
        cache.register(c)

    caps = list(cache.iter_phase(low.phase, low.tier))
    assert caps == [high, mid, low], "Capabilities should sort by -priority"


def test_phase_tier_isolation():
    cache = CapabilityCache()
    a = make_cap(priority=1, phase=StepPhase.GATHER_CONTEXT, tier=Tier.NODE)
    b = make_cap(priority=1, phase=StepPhase.RENDER, tier=Tier.NODE)
    c = make_cap(priority=1, phase=StepPhase.GATHER_CONTEXT, tier=Tier.GRAPH)

    for cap in (a, b, c):
        cache.register(cap)

    # Only 'a' matches its exact (phase, tier)
    assert list(cache.iter_phase(StepPhase.GATHER_CONTEXT, Tier.NODE)) == [a]
    # Empty when nothing registered
    assert list(cache.iter_phase(StepPhase.APPLY_EFFECTS, Tier.DOMAIN)) == []
