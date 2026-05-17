"""Domain-local dispatch chains for sandbox simulation refinement."""

from __future__ import annotations

from tangl.core import BehaviorRegistry, CallReceipt, DispatchLayer, Selector

from .time import SandboxTickEvent


sandbox_dispatch = BehaviorRegistry(
    label="sandbox_dispatch",
    default_dispatch_layer=DispatchLayer.SYSTEM,
)
"""Behavior registry for sandbox-local subphases."""


def on_sandbox_tick(func=None, **kwargs):
    """Register a handler for one normalized sandbox tick."""
    if func is None:
        return lambda f: sandbox_dispatch.register(
            func=f,
            task="sandbox_tick",
            **kwargs,
        )
    return sandbox_dispatch.register(func=func, task="sandbox_tick", **kwargs)


def do_sandbox_tick(caller, *, ctx, clock_tick: int, **kwargs) -> list[SandboxTickEvent]:
    """Run sandbox tick consumers and return produced tick events."""
    receipts = sandbox_dispatch.execute_all(
        task="sandbox_tick",
        call_kwargs={"caller": caller, "clock_tick": clock_tick, **kwargs},
        ctx=ctx,
        selector=Selector(caller_kind=type(caller)),
    )
    events: list[SandboxTickEvent] = []
    for result in CallReceipt.gather_results(*receipts):
        if isinstance(result, SandboxTickEvent):
            events.append(result)
            continue
        if isinstance(result, list):
            for item in result:
                if not isinstance(item, SandboxTickEvent):
                    raise TypeError(
                        "sandbox_tick list entries must be SandboxTickEvent instances"
                    )
                events.append(item)
            continue
        raise TypeError(
            f"sandbox_tick handlers must return SandboxTickEvent values, got {type(result)!r}"
        )
    return events


__all__ = [
    "do_sandbox_tick",
    "on_sandbox_tick",
    "sandbox_dispatch",
]
