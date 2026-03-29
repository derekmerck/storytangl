"""Tests for the ComfyUI HTTP client.

Organized by functionality:
- Workflow submission: queue prompt request shape and prompt id parsing
- History and outputs: pending/completed history handling and image ref extraction
- Binary fetches: image bytes retrieval against the Comfy view endpoint
"""

from __future__ import annotations

from unittest.mock import Mock, patch

from tangl.media.media_creators.comfy_forge import ComfyApi, ComfyWorkflow


def _response(*, json_data=None, content: bytes = b"") -> Mock:
    response = Mock()
    response.json.return_value = json_data
    response.content = content
    response.raise_for_status.return_value = None
    return response


class TestComfyApiSubmission:
    """Tests for Comfy prompt submission behavior."""

    def test_queue_prompt_posts_workflow_json_and_returns_prompt_id(self) -> None:
        api = ComfyApi("titan2.lan:8188")
        workflow = {"1": {"inputs": {"text": "portrait"}}}

        with patch(
            "tangl.media.media_creators.comfy_forge.comfy_api.requests.post",
            return_value=_response(json_data={"prompt_id": "abc123"}),
        ) as post:
            prompt_id = api.queue_prompt(workflow)

        assert prompt_id == "abc123"
        post.assert_called_once_with(
            "http://titan2.lan:8188/prompt",
            json={"prompt": workflow},
        )

    def test_queue_prompt_accepts_comfy_workflow_wrapper(self) -> None:
        api = ComfyApi()
        workflow = ComfyWorkflow(spec={"1": {"inputs": {"text": "portrait"}}})

        with patch(
            "tangl.media.media_creators.comfy_forge.comfy_api.requests.post",
            return_value=_response(json_data={"prompt_id": "wrapped"}),
        ):
            prompt_id = api.queue_prompt(workflow)

        assert prompt_id == "wrapped"


class TestComfyApiHistory:
    """Tests for history and output parsing behavior."""

    def test_get_history_returns_none_for_pending_prompt(self) -> None:
        api = ComfyApi()

        with patch(
            "tangl.media.media_creators.comfy_forge.comfy_api.requests.get",
            return_value=_response(json_data={}),
        ):
            history = api.get_history("pending-1")

        assert history is None

    def test_get_history_returns_completed_prompt_entry(self) -> None:
        api = ComfyApi()
        payload = {"prompt-1": {"outputs": {"save": {"images": []}}}}

        with patch(
            "tangl.media.media_creators.comfy_forge.comfy_api.requests.get",
            return_value=_response(json_data=payload),
        ):
            history = api.get_history("prompt-1")

        assert history == payload["prompt-1"]

    def test_get_output_image_refs_extracts_output_images(self) -> None:
        api = ComfyApi()
        payload = {
            "prompt-1": {
                "outputs": {
                    "save": {
                        "images": [
                            {
                                "filename": "hero.png",
                                "subfolder": "",
                                "type": "output",
                            }
                        ]
                    }
                }
            }
        }

        with patch(
            "tangl.media.media_creators.comfy_forge.comfy_api.requests.get",
            return_value=_response(json_data=payload),
        ):
            refs = api.get_output_image_refs("prompt-1")

        assert refs == [
            {
                "filename": "hero.png",
                "subfolder": "",
                "type": "output",
            }
        ]


class TestComfyApiIntrospection:
    """Tests for model and capability introspection helpers."""

    def test_list_model_types_reads_models_endpoint(self) -> None:
        api = ComfyApi()

        with patch(
            "tangl.media.media_creators.comfy_forge.comfy_api.requests.get",
            return_value=_response(json_data=["checkpoints", "loras"]),
        ) as get:
            model_types = api.list_model_types()

        assert model_types == ["checkpoints", "loras"]
        get.assert_called_once_with("http://127.0.0.1:8188/models")

    def test_describe_worker_collects_models_embeddings_and_system_stats(self) -> None:
        api = ComfyApi()
        responses = [
            _response(json_data=["checkpoints", "loras"]),
            _response(json_data=["sdxl.safetensors"]),
            _response(json_data=["embedding-a"]),
            _response(json_data={"system": {"os": "linux"}}),
        ]

        with patch(
            "tangl.media.media_creators.comfy_forge.comfy_api.requests.get",
            side_effect=responses,
        ):
            snapshot = api.describe_worker()

        assert snapshot.url == "http://127.0.0.1:8188"
        assert snapshot.model_types == ("checkpoints", "loras")
        assert snapshot.models_by_folder == {"checkpoints": ("sdxl.safetensors",)}
        assert snapshot.embeddings == ("embedding-a",)
        assert snapshot.system_stats == {"system": {"os": "linux"}}


class TestComfyApiControlAndBinaryFetches:
    """Tests for queue control and raw image retrieval."""

    def test_cancel_prompt_posts_queue_delete_payload(self) -> None:
        api = ComfyApi("http://127.0.0.1:9000")

        with patch(
            "tangl.media.media_creators.comfy_forge.comfy_api.requests.post",
            return_value=_response(json_data={"deleted": ["prompt-1"]}),
        ) as post:
            payload = api.cancel_prompt("prompt-1")

        assert payload == {"deleted": ["prompt-1"]}
        post.assert_called_once_with(
            "http://127.0.0.1:9000/queue",
            json={"delete": ["prompt-1"]},
        )

    def test_interrupt_posts_to_interrupt_endpoint(self) -> None:
        api = ComfyApi("http://127.0.0.1:9000")

        with patch(
            "tangl.media.media_creators.comfy_forge.comfy_api.requests.post",
            return_value=_response(json_data={}),
        ) as post:
            payload = api.interrupt()

        assert payload == {}
        post.assert_called_once_with("http://127.0.0.1:9000/interrupt")

    def test_fetch_image_bytes_passes_expected_view_params(self) -> None:
        api = ComfyApi("http://127.0.0.1:9000")

        with patch(
            "tangl.media.media_creators.comfy_forge.comfy_api.requests.get",
            return_value=_response(content=b"png-bytes"),
        ) as get:
            data = api.fetch_image_bytes(
                "hero.png",
                subfolder="story",
                folder_type="output",
            )

        assert data == b"png-bytes"
        get.assert_called_once_with(
            "http://127.0.0.1:9000/view",
            params={
                "filename": "hero.png",
                "subfolder": "story",
                "type": "output",
            },
        )
