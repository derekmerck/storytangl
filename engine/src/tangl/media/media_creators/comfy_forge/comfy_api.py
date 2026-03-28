from __future__ import annotations

import json
from dataclasses import dataclass
from io import TextIOBase
from typing import Any
from urllib.parse import urlparse

import requests


def _normalize_title(value: str) -> str:
    return value.strip().casefold().replace(" ", "_")


@dataclass
class ComfyWorkflow:
    """Wrapper with small node-title helpers for ComfyUI workflow dicts."""

    spec: dict[str, dict]

    @staticmethod
    def _get_node(spec: dict[str, dict], title: str) -> dict:
        normalized = _normalize_title(title)
        for node in spec.values():
            meta = node.get("_meta")
            node_title = meta.get("title") if isinstance(meta, dict) else None
            if isinstance(node_title, str) and _normalize_title(node_title) == normalized:
                return node
        raise KeyError(f"No Comfy workflow node titled {title!r}")

    @staticmethod
    def _infer_input_key(inputs: dict[str, object]) -> str:
        preferred = (
            "text",
            "image",
            "ckpt_name",
            "seed",
            "steps",
            "sampler_name",
            "width",
            "height",
        )
        for key in preferred:
            if key in inputs:
                return key
        if len(inputs) == 1:
            return next(iter(inputs))
        raise KeyError(f"Unable to infer input key from {sorted(inputs)}")

    @classmethod
    def from_json(cls, data: str | TextIOBase) -> "ComfyWorkflow":
        if isinstance(data, str):
            payload = json.loads(data)
        elif isinstance(data, TextIOBase):
            payload = json.load(data)
        else:
            raise TypeError(f"Expected str or TextIOBase, got {type(data)!r}")
        if not isinstance(payload, dict):
            raise TypeError("Comfy workflow JSON must decode to a dict")
        return cls(spec=payload)

    def get_node(self, title: str) -> dict:
        return self._get_node(self.spec, title)

    def set_input_value(self, title: str, value: object, *, key: str | None = None) -> None:
        node = self.get_node(title)
        inputs = node.get("inputs")
        if not isinstance(inputs, dict):
            raise KeyError(f"Workflow node {title!r} does not expose inputs")
        input_key = key or self._infer_input_key(inputs)
        if input_key not in inputs:
            raise KeyError(f"Workflow node {title!r} has no input {input_key!r}")
        inputs[input_key] = value


@dataclass(frozen=True)
class ComfyWorkerSnapshot:
    """Small capability snapshot for one ComfyUI worker."""

    url: str
    model_types: tuple[str, ...]
    models_by_folder: dict[str, tuple[str, ...]]
    embeddings: tuple[str, ...]
    system_stats: dict[str, Any]


class ComfyApi:
    """Thin HTTP client for the subset of the ComfyUI API used by the worker flow."""

    def __init__(self, url: str = "http://127.0.0.1:8188") -> None:
        if "://" not in url:
            url = f"http://{url}"
        parsed = urlparse(url)
        protocol = parsed.scheme or "http"
        host = parsed.hostname or "127.0.0.1"
        port = parsed.port or (443 if protocol == "https" else 8188)
        self._base_url = f"{protocol}://{host}:{port}"

    def endpoint(self, path: str = "") -> str:
        path = path.lstrip("/")
        return f"{self._base_url}/{path}" if path else self._base_url

    def queue_prompt(self, workflow: dict[str, dict] | ComfyWorkflow) -> str:
        payload = workflow.spec if isinstance(workflow, ComfyWorkflow) else workflow
        response = requests.post(self.endpoint("prompt"), json={"prompt": payload})
        response.raise_for_status()
        prompt_id = response.json().get("prompt_id")
        if not isinstance(prompt_id, str) or not prompt_id:
            raise ValueError("ComfyUI did not return a prompt_id")
        return prompt_id

    def get_queue_status(self) -> dict[str, object]:
        response = requests.get(self.endpoint("prompt"))
        response.raise_for_status()
        payload = response.json()
        return payload.get("exec_info", {}) if isinstance(payload, dict) else {}

    def get_queue(self) -> dict[str, Any]:
        response = requests.get(self.endpoint("queue"))
        response.raise_for_status()
        payload = response.json()
        return payload if isinstance(payload, dict) else {}

    def get_history(self, prompt_id: str | None = None) -> dict | None:
        endpoint = f"history/{prompt_id}" if prompt_id is not None else "history"
        response = requests.get(self.endpoint(endpoint))
        response.raise_for_status()
        payload = response.json()
        if prompt_id is None:
            return payload if isinstance(payload, dict) else None
        if not isinstance(payload, dict) or not payload:
            return None
        if prompt_id in payload and isinstance(payload[prompt_id], dict):
            return payload[prompt_id]
        if "outputs" in payload or "status" in payload:
            return payload
        return None

    def get_output_image_refs(self, prompt_id: str) -> list[dict[str, str]]:
        history = self.get_history(prompt_id)
        return self.extract_output_image_refs(history)

    @staticmethod
    def extract_output_image_refs(history: dict[str, Any] | None) -> list[dict[str, str]]:
        if not isinstance(history, dict):
            return []

        outputs = history.get("outputs")
        if not isinstance(outputs, dict):
            return []

        refs: list[dict[str, str]] = []
        for node_output in outputs.values():
            if not isinstance(node_output, dict):
                continue
            images = node_output.get("images")
            if not isinstance(images, list):
                continue
            for image in images:
                if not isinstance(image, dict):
                    continue
                filename = image.get("filename")
                if not isinstance(filename, str) or not filename:
                    continue
                refs.append(
                    {
                        "filename": filename,
                        "subfolder": str(image.get("subfolder") or ""),
                        "type": str(image.get("type") or "output"),
                    }
                )
        return refs

    def fetch_image_bytes(
        self,
        filename: str,
        *,
        subfolder: str = "",
        folder_type: str = "output",
    ) -> bytes:
        response = requests.get(
            self.endpoint("view"),
            params={
                "filename": filename,
                "subfolder": subfolder,
                "type": folder_type,
            },
        )
        response.raise_for_status()
        return response.content

    def list_model_types(self) -> list[str]:
        response = requests.get(self.endpoint("models"))
        response.raise_for_status()
        payload = response.json()
        return [str(item) for item in payload] if isinstance(payload, list) else []

    def list_models(self, folder: str) -> list[str]:
        response = requests.get(self.endpoint(f"models/{folder}"))
        response.raise_for_status()
        payload = response.json()
        return [str(item) for item in payload] if isinstance(payload, list) else []

    def list_embeddings(self) -> list[str]:
        response = requests.get(self.endpoint("embeddings"))
        response.raise_for_status()
        payload = response.json()
        return [str(item) for item in payload] if isinstance(payload, list) else []

    def get_object_info(self, node_class: str | None = None) -> dict[str, Any]:
        endpoint = f"object_info/{node_class}" if node_class is not None else "object_info"
        response = requests.get(self.endpoint(endpoint))
        response.raise_for_status()
        payload = response.json()
        return payload if isinstance(payload, dict) else {}

    def get_system_stats(self) -> dict[str, Any]:
        response = requests.get(self.endpoint("system_stats"))
        response.raise_for_status()
        payload = response.json()
        return payload if isinstance(payload, dict) else {}

    def describe_worker(
        self,
        *,
        model_folders: tuple[str, ...] = ("checkpoints",),
    ) -> ComfyWorkerSnapshot:
        available_types = tuple(self.list_model_types())
        models_by_folder = {
            folder: tuple(self.list_models(folder))
            for folder in model_folders
            if folder in available_types
        }
        return ComfyWorkerSnapshot(
            url=self.endpoint(),
            model_types=available_types,
            models_by_folder=models_by_folder,
            embeddings=tuple(self.list_embeddings()),
            system_stats=self.get_system_stats(),
        )

    def cancel_prompt(self, prompt_id: str) -> dict[str, Any]:
        response = requests.post(
            self.endpoint("queue"),
            json={"delete": [prompt_id]},
        )
        response.raise_for_status()
        try:
            payload = response.json()
        except ValueError:
            return {}
        return payload if isinstance(payload, dict) else {}

    def interrupt(self) -> dict[str, Any]:
        response = requests.post(self.endpoint("interrupt"))
        response.raise_for_status()
        try:
            payload = response.json()
        except ValueError:
            return {}
        return payload if isinstance(payload, dict) else {}
