from __future__ import annotations

import time
from typing import TYPE_CHECKING

from ._common import configured_comfy_url, history_error
from .comfy_api import ComfyApi

if TYPE_CHECKING:
    from .comfy_spec import ComfySpec


class ComfyForge:
    """Blocking ComfyUI creator for ``FAST_SYNC`` media generation."""

    def __init__(
        self,
        *,
        url: str = "http://127.0.0.1:8188",
        timeout_seconds: float = 120.0,
        poll_interval_seconds: float = 1.0,
        api: ComfyApi | None = None,
    ) -> None:
        self._timeout_seconds = timeout_seconds
        self._poll_interval_seconds = poll_interval_seconds
        self._api = api or ComfyApi(url)

    @classmethod
    def from_settings(cls) -> "ComfyForge | None":
        url = configured_comfy_url()
        if not url:
            return None
        return cls(url=url)

    def create_media(self, spec: "ComfySpec") -> tuple[bytes, "ComfySpec"]:
        spec.commit_deterministic_seed()
        spec.workflow = spec.materialize_workflow()
        prompt_id = self._api.queue_prompt(spec.workflow)

        deadline = time.monotonic() + self._timeout_seconds
        while time.monotonic() < deadline:
            history = self._api.get_history(prompt_id)
            if history is None:
                time.sleep(self._poll_interval_seconds)
                continue

            error = history_error(history)
            if error is not None:
                raise RuntimeError(f"ComfyUI execution failed: {error}")

            image_refs = self._api.extract_output_image_refs(history)
            if image_refs:
                image_ref = image_refs[0]
                image_bytes = self._api.fetch_image_bytes(
                    image_ref["filename"],
                    subfolder=image_ref.get("subfolder", ""),
                    folder_type=image_ref.get("type", "output"),
                )
                return image_bytes, spec

            status = history.get("status")
            if isinstance(status, dict) and status.get("completed") is False:
                time.sleep(self._poll_interval_seconds)
                continue

            raise RuntimeError("ComfyUI workflow completed with no output images")

        raise TimeoutError(f"Timed out waiting for ComfyUI prompt {prompt_id}")
