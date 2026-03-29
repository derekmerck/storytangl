from __future__ import annotations

from enum import Enum
from html import escape
from uuid import UUID

from tangl.core import Priority
from tangl.journal.fragments import ContentFragment
from tangl.media.media_creators.media_spec import MediaResolutionClass, MediaSpec
from tangl.media.media_data_type import MediaDataType
from tangl.story import Block, on_journal


class LogicGateType(str, Enum):
    """Allowed phase-1 gate roles for logic demo blocks."""

    INPUT = "INPUT"
    OUTPUT = "OUTPUT"
    XOR = "XOR"
    AND = "AND"
    OR = "OR"


class LogicBlock(Block):
    """Typed block used by the logic demo world."""

    gate_type: LogicGateType


_GATE_COLORS: dict[LogicGateType, str] = {
    LogicGateType.INPUT: "#f5d90a",
    LogicGateType.OUTPUT: "#3ac47d",
    LogicGateType.XOR: "#4f83ff",
    LogicGateType.AND: "#ff8c42",
    LogicGateType.OR: "#d946ef",
}

_PROSE_BY_LABEL: dict[str, str] = {
    "choose_machine": "Choose a logic machine to inspect.",
    "parity_first_input": "Parity checker: enter the first bit.",
    "parity_even_state": "The XOR accumulator is even so far. Enter the second bit.",
    "parity_odd_state": "The XOR accumulator is odd so far. Enter the second bit.",
    "parity_even_output": "Parity result: the two-bit input is even.",
    "parity_odd_output": "Parity result: the two-bit input is odd.",
    "half_adder_pick_a": "Half adder: choose the value of input A.",
    "half_adder_a_zero": "Input A is 0. Choose the value of input B.",
    "half_adder_a_one": "Input A is 1. Choose the value of input B.",
    "half_adder_xor_00": "XOR stage resolves the sum bit to 0.",
    "half_adder_xor_01": "XOR stage resolves the sum bit to 1.",
    "half_adder_xor_10": "XOR stage resolves the sum bit to 1.",
    "half_adder_xor_11": "XOR stage resolves the sum bit to 0.",
    "half_adder_and_00": "AND stage resolves the carry bit to 0.",
    "half_adder_and_01": "AND stage resolves the carry bit to 0.",
    "half_adder_and_10": "AND stage resolves the carry bit to 0.",
    "half_adder_and_11": "AND stage resolves the carry bit to 1.",
    "half_adder_output_00": "Half-adder output: sum 0, carry 0.",
    "half_adder_output_10": "Half-adder output: sum 1, carry 0.",
    "half_adder_output_01": "Half-adder output: sum 0, carry 1.",
    "full_adder_pick_a": "Full adder: choose the value of input A.",
    "full_adder_a_zero": "Input A is 0. Choose the value of input B.",
    "full_adder_a_one": "Input A is 1. Choose the value of input B.",
    "full_adder_ab_00": "Inputs A and B are both 0. Choose the carry-in bit.",
    "full_adder_ab_01": "Inputs A and B are 0 and 1. Choose the carry-in bit.",
    "full_adder_ab_10": "Inputs A and B are 1 and 0. Choose the carry-in bit.",
    "full_adder_ab_11": "Inputs A and B are both 1. Choose the carry-in bit.",
}


def logic_prose_for_block(block: LogicBlock) -> str:
    """Return deterministic prose for one already-resolved logic block."""

    label = block.get_label()
    prose = _PROSE_BY_LABEL.get(label)
    if prose is not None:
        return prose
    if label.startswith("full_adder_xor_"):
        return "Full-adder XOR stage resolves the sum bit."
    if label.startswith("full_adder_or_"):
        return "Full-adder carry-combine stage resolves the carry bit."
    if label.startswith("full_adder_output_"):
        suffix = label.removeprefix("full_adder_output_").split("_sc", 1)[-1]
        if len(suffix) == 2:
            return f"Full-adder output: sum {suffix[0]}, carry {suffix[1]}."
    return f"{block.gate_type.value} node {block.get_label()}."


@on_journal(
    wants_caller_kind=LogicBlock,
    wants_exact_kind=False,
    priority=Priority.EARLY,
)
def render_logic_block_content(*, caller, ctx, **_kw):
    """Emit domain-local prose for logic blocks."""

    if not isinstance(caller, LogicBlock):
        return None
    return ContentFragment(
        content=logic_prose_for_block(caller),
        source_id=caller.uid,
    )


class GateBadgeSpec(MediaSpec):
    """Small deterministic SVG badge for logic demo nodes."""

    resolution_class: MediaResolutionClass = MediaResolutionClass.FAST_SYNC
    data_type: MediaDataType = MediaDataType.VECTOR

    gate_type: LogicGateType
    badge_text: str = ""
    width: int = 88
    height: int = 28

    @classmethod
    def get_creation_service(cls) -> "GateBadgeForge":
        return GateBadgeForge()


class GateBadgeForge:
    """Minimal sync creator for logic gate badges."""

    def create_media(self, spec: GateBadgeSpec) -> tuple[str, GateBadgeSpec]:
        color = _GATE_COLORS.get(spec.gate_type, "#9aa4b2")
        text = escape(spec.badge_text or spec.gate_type.value)
        svg = (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{spec.width}" '
            f'height="{spec.height}" viewBox="0 0 {spec.width} {spec.height}">'
            f'<rect x="1" y="1" width="{spec.width - 2}" height="{spec.height - 2}" '
            f'rx="7" fill="{color}" stroke="#102a43" stroke-width="2"/>'
            f'<text x="{spec.width / 2}" y="{(spec.height / 2) + 4}" '
            'font-family="monospace" font-size="12" text-anchor="middle" '
            'fill="#102a43">'
            f"{text}</text>"
            "</svg>"
        )
        return svg, spec


LogicBlock.model_rebuild(_types_namespace={"UUID": UUID})


__all__ = [
    "GateBadgeSpec",
    "LogicBlock",
    "LogicGateType",
    "logic_prose_for_block",
]
