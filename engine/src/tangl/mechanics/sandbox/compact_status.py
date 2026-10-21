"""Opt-in compact disclosure contributors for a sandbox world's authority."""

from __future__ import annotations

from tangl.core import Selector
from tangl.presentation.hints import PresentationHints
from tangl.presentation.projection import (
    InfoAffordance, ProjectedSection, ProjectedState, ProjectionRequest, ScalarValue,
)
from tangl.story import Block, Scene
from tangl.vm.runtime.frame import PhaseCtx

from .scope import SandboxScope
from .location import SandboxLocation
from .story_info import DEFAULT_PERIOD_LABELS, _period_label, sandbox_asset_items
from .time import current_world_time


def advertise_compact_status(
    *, caller: Block, ctx: PhaseCtx, **_kw: object,
) -> list[InfoAffordance]:
    """Offer status throughout the shared scope, not only on location menus."""
    if isinstance(ctx.get_ns().get("sandbox_scope_node"), SandboxScope):
        return [InfoAffordance(channel_id="ui-status", label="Current status")]
    return []


def project_compact_status(
    *, caller: Block, ctx: PhaseCtx, request: ProjectionRequest, **_kw: object,
) -> list[ProjectedSection]:
    """Disclose a small ordered status set; nearest scoped sections may replace it."""
    if "ui-status" not in request.requested_channels():
        return []
    ns = ctx.get_ns()
    scope = ns.get("sandbox_scope_node")
    if not isinstance(scope, SandboxScope):
        return []
    if "ui_status" in ns:
        return ProjectedState.model_validate({"sections": ns["ui_status"] or []}).sections
    scene = next(Selector(has_kind=Scene).filter(caller.ancestors), None)
    title = (scene.title or scene.label) if scene is not None else caller.label
    if isinstance(caller, SandboxLocation):
        title = caller.location_name or title
    time = current_world_time(scope)
    period = _period_label(time.period, ns.get("period_labels", DEFAULT_PERIOD_LABELS))
    period_icon = ns.get("period_icons", {}).get(str(time.period))
    sections = [
        ProjectedSection(section_id="scene", title="Scene", value=ScalarValue(value=title),
                         hints=PresentationHints(icon="scene")),
        ProjectedSection(section_id="period", title="Period", value=ScalarValue(value=period),
                         hints=PresentationHints(icon=period_icon)),
        ProjectedSection(section_id="day", title="Day",
                         value=ScalarValue(value=f"Day {time.run_day}"),
                         hints=PresentationHints(icon="calendar")),
    ]
    # This provider chooses entries and order; the client never joins private inventory.
    items = sandbox_asset_items(scope.player_assets)
    for asset, item in zip(sorted(scope.player_assets.assets), items):
        sections.append(ProjectedSection(
            section_id=f"item:{asset}", title=item.label,
            value=ScalarValue(value=item.detail or "carried"),
            hints=PresentationHints(icon="inventory"),
        ))
    return sections
