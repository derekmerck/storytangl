"""Test journal subtask registration decorators."""
from __future__ import annotations

from tangl.story.dispatch import (
    on_gather_choices,
    on_gather_content,
    on_post_process_content,
)
from tangl.story.episode import Block


def test_gather_content_decorator_registers():
    """`on_gather_content` should register without errors."""

    @on_gather_content(caller=Block)
    def test_handler(cursor, *, ctx, **kwargs):  # noqa: ARG001
        return "test"

    assert test_handler is not None


def test_post_process_content_decorator_registers():
    """`on_post_process_content` should register without errors."""

    @on_post_process_content(caller=Block)
    def test_handler(cursor, *, ctx, **kwargs):  # noqa: ARG001
        return []

    assert test_handler is not None


def test_gather_choices_decorator_registers():
    """`on_gather_choices` should register without errors."""

    @on_gather_choices(caller=Block)
    def test_handler(cursor, *, ctx, **kwargs):  # noqa: ARG001
        return []

    assert test_handler is not None
