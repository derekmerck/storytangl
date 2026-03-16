from __future__ import annotations

from tangl.service.hooks import GatewayHooks
from tangl.service.operations import ServiceOperation


def test_default_hooks_media_url_profile_populates_missing_media_url() -> None:
    hooks = GatewayHooks()
    hooks.install_default_hooks()

    payload = {
        "fragments": [
            {
                "fragment_type": "media",
                "scope": "world",
                "label": "intro.svg",
            },
            {
                "fragment_type": "media",
                "scope": "sys",
                "source_label": "logo.svg",
            },
            {
                "fragment_type": "content",
                "text": "hello",
            },
        ]
    }

    transformed = hooks.run_outbound(
        payload,
        operation=ServiceOperation.STORY_UPDATE,
        render_profile="raw+media_url",
        user_id="user-1",
    )

    fragments = transformed["fragments"]
    assert fragments[0]["url"] == "/media/world/intro.svg"
    assert fragments[1]["url"] == "/media/sys/logo.svg"
    assert "url" not in fragments[2]


def test_default_hooks_media_url_profile_preserves_existing_url() -> None:
    hooks = GatewayHooks()
    hooks.install_default_hooks()

    payload = {
        "fragment_type": "media",
        "scope": "world",
        "label": "intro.svg",
        "url": "https://cdn.example/intro.svg",
    }

    transformed = hooks.run_outbound(
        payload,
        operation=ServiceOperation.STORY_UPDATE,
        render_profile="media_url",
        user_id="user-1",
    )

    assert transformed["url"] == "https://cdn.example/intro.svg"


def test_default_hooks_media_url_profile_does_not_fake_url_for_inline_media() -> None:
    hooks = GatewayHooks()
    hooks.install_default_hooks()

    payload = {
        "fragment_type": "media",
        "content_format": "data",
        "data": "<svg xmlns='http://www.w3.org/2000/svg'></svg>",
        "scope": "world",
    }

    transformed = hooks.run_outbound(
        payload,
        operation=ServiceOperation.STORY_UPDATE,
        render_profile="media_url",
        user_id="user-1",
    )

    assert "url" not in transformed
