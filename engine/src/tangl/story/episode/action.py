from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from pydantic import field_serializer

from tangl.ir.story_ir.choice_disclosure import UnavailableChoiceDisclosure
from tangl.presentation.intent import (
    Accepts,
    EnumValidator,
    LengthValidator,
    RegexValidator,
    TextAccepts,
    Blocker,
    UIHints,
)
from tangl.vm import ResolutionPhase, TraversableEdge


class Action(TraversableEdge):
    """Action()

    Traversable choice edge connecting story blocks.

    Why
    ----
    ``Action`` carries both user-facing choice text and authored successor
    semantics, allowing the compiler and materializer to preserve the narrative
    meaning of redirects, continuations, and interactive choices.
    """

    text: str = ""
    # Generated edge labels identify bindings, not player-facing wording.
    fallback_text: str = ""
    successor_ref: str | None = None
    activation: str | None = None
    payload: Any = None
    accepts: Accepts | None = None
    blockers: list[Blocker] | None = None
    unavailable_choice_disclosure: UnavailableChoiceDisclosure | None = None
    ui_hints: UIHints | None = None
    journal_text: str | None = None

    def validate_payload(self, payload: Any) -> bool:
        """Enforce explicit text declarations on the effective payload before movement.

        BackendValidator is only a marker; domain restrictions still use ordinary
        Action/world validation handlers. No input is normalized or coerced here.
        """
        accepts = self.accepts
        if not isinstance(accepts, TextAccepts):
            return True
        if not isinstance(payload, Mapping) or not isinstance(payload.get("text"), str):
            raise ValueError("Text input must be a string in payload['text'].")
        text = payload["text"]
        if accepts.required and not text.strip():
            raise ValueError("Text input is required.")
        for validator in accepts.validators:
            if isinstance(validator, LengthValidator):
                if validator.min is not None and len(text) < validator.min:
                    raise ValueError(f"Use at least {validator.min} characters.")
                if validator.max is not None and len(text) > validator.max:
                    raise ValueError(f"Use at most {validator.max} characters.")
            elif isinstance(validator, RegexValidator):
                flags = re.NOFLAG
                supported = {"i": re.IGNORECASE, "m": re.MULTILINE, "s": re.DOTALL}
                for flag in validator.flags or "":
                    if flag not in supported:
                        raise ValueError(f"Unsupported text regex flags: {validator.flags!r}")
                    flags |= supported[flag]
                try:
                    pattern = re.compile(validator.pattern, flags)
                except re.error as exc:
                    raise ValueError(f"Invalid text regex: {exc}") from exc
                if pattern.search(text) is None:
                    raise ValueError(validator.message or "Does not match the expected pattern.")
            elif isinstance(validator, EnumValidator):
                value = text if validator.case_sensitive else text.lower()
                values = validator.values if validator.case_sensitive else [
                    item.lower() for item in validator.values
                ]
                if value not in values:
                    raise ValueError(f"Use one of: {', '.join(validator.values)}")
        return True

    @field_serializer("accepts")
    def _serialize_accepts(self, accepts: Accepts | None) -> dict[str, Any] | None:
        if accepts is None:
            return None
        return accepts.model_dump(mode="python", by_alias=True, exclude_none=True)

    @classmethod
    def trigger_phase_from_activation(cls, activation: str | None) -> ResolutionPhase | None:
        """Map authored activation shorthands to vm resolution phases."""
        if activation == "first":
            return ResolutionPhase.PREREQS
        if activation == "last":
            return ResolutionPhase.POSTREQS
        return None
