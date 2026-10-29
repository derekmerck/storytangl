"""Generic optional carried-item facts shared by real status and CLI witnesses."""
from __future__ import annotations

from pathlib import Path
import shutil

from tangl.media.media_resource.resource_manager import ResourceManager
from tangl.presentation import PresentationHints
from tangl.presentation.projection import (
    InfoAffordance, ProjectedSection, ProjectionRequest, ScalarValue,
)
from tangl.story import Block, World
from tangl.vm.runtime.frame import PhaseCtx


ITEMS = (
    ("pass", "Hall pass", "key", "HP"),
    ("token", "Brass token", "inventory", "BT"),
    ("pouch", "Canvas pouch", "bag", "CP"),
)


def icon_world(
    root: Path, label: str = "status_icon_witness", *, pass_hints: PresentationHints | None = None,
) -> World:
    root.mkdir(parents=True, exist_ok=True)
    fixtures = Path(__file__).resolve().parents[1] / "resources/status_icons"
    for source in fixtures.glob("*.svg"):
        shutil.copyfile(source, root / source.name)
    resources = ResourceManager(root)
    resources.index_directory(".")
    world = World.from_script_data(script_data={
        "label": label, "metadata": {"start_at": "desk.start"},
        "globals": {"item_hints": {
            key: (pass_hints if key == "pass" and pass_hints is not None else PresentationHints(
                icon_media=f"{key}.svg", icon=token, short_label=short,
                icon_only=True, placement="middle",
            )).model_dump() for key, _title, token, short in ITEMS
        }},
        "scenes": {"desk": {"blocks": {
            "start": {
                "content": "Three optional carried items.",
                "locals": {"owned": ["pass", "token", "pouch"]},
                "actions": [
                    {"text": "Leave the pass", "successor": "without_pass"},
                    {"text": "Revisit", "successor": "start"},
                ],
            },
            "without_pass": {
                "content": "The pass is on the desk.",
                "locals": {"owned": ["token", "pouch"]},
                "actions": [{"text": "Take the pass", "successor": "start"}],
            },
        }}},
    }, resources=resources)

    def advertise(**_kwargs: object) -> list[InfoAffordance]:
        return [InfoAffordance(channel_id="ui-status", label="Status"),
                InfoAffordance(channel_id="ui-inventory", label="Inventory", shortcuts=["inv"])]

    def project(
        *, ctx: PhaseCtx, request: ProjectionRequest, **_kwargs: object,
    ) -> list[ProjectedSection] | None:
        if not {"ui-status", "ui-inventory"}.intersection(request.requested_channels()):
            return None
        owned = ctx.get_ns()["owned"]
        return [ProjectedSection(
            section_id=key, title=title, value=ScalarValue(value="Carried"),
            hints=PresentationHints.model_validate(ctx.get_ns()["item_hints"][key]),
        ) for key, title, token, short in ITEMS if key in owned]

    world.dispatch.register(advertise, task="advertise_story_info_channels",
                            wants_caller_kind=Block, wants_exact_kind=False)
    world.dispatch.register(project, task="get_story_info",
                            wants_caller_kind=Block, wants_exact_kind=False)
    return world
