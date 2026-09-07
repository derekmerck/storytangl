"""Presentation contributor registration contracts."""

from __future__ import annotations

from collections.abc import Callable

import pytest

from tangl.core import Selector
from tangl.presentation.dispatch import (
    on_advertise_info_channels,
    on_get_story_info,
    presentation_dispatch,
)


@pytest.mark.parametrize(
    ("decorator", "task"),
    (
        (on_advertise_info_channels, "advertise_info_channels"),
        (on_get_story_info, "get_story_info"),
    ),
)
def test_presentation_decorators_register_and_execute(
    decorator: Callable,
    task: str,
) -> None:
    caller = object()

    @decorator
    def contributor(*, caller: object, ctx: object) -> str:
        return task

    receipts = presentation_dispatch.execute_all(
        task=task,
        call_kwargs={"caller": caller},
        selector=Selector(caller_kind=type(caller)),
    )

    assert [receipt.result for receipt in receipts] == [task]
