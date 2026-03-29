from __future__ import annotations

import time

import logging

import json
from pprint import pformat
from io import TextIOWrapper, BytesIO
from urllib.parse import urlparse
from logging import getLogger
from pprint import pprint

import requests
from PIL import Image

logger = getLogger('tangl.media.sf')
logger.setLevel(logging.INFO)

class ComfyWorkflow:
    """
    Wrapper class with basic node accessors for a comfy job workflow dict.
    """

    def __init__(self, spec: dict):
        self.spec = spec

    @staticmethod
    def _get_node(spec, label):
        for node in spec.values():
            if node['_meta']['title'].lower().replace(' ', "_") == label.lower().replace(' ', "_"):
                return node
        raise KeyError(f"No node {label}")

    @staticmethod
    def _infer_key(inputs):
        for item in ['text', 'image']:
            if item in inputs:
                return item
        raise KeyError(f"neither 'text' nor 'image' in inputs {inputs}")

    @staticmethod
    def _get_input(spec, label):
        node = ComfyWorkflow._get_node(spec, label)
        inputs = node.get('inputs')
        if inputs:
            key = ComfyWorkflow._infer_key(inputs)
            return inputs[key]

    @staticmethod
    def _set_input_value(spec, label, value, index=0):
        node = ComfyWorkflow._get_node(spec, label)
        if 'inputs' not in node:
            raise KeyError(f"No 'inputs' in node {node}")
        key = ComfyWorkflow._infer_key(node['inputs'])
        node['inputs'][key] = value

    def set_input_value(self, label, value, index=0):
        self._set_input_value(self.spec, label, value, index)

    def get_inputs(self, label):
        return self._get_input(self.spec, label)

    @classmethod
    def from_json(cls, data=str | TextIOWrapper):
        if isinstance(data, str):
            _data = json.loads(data)
        elif isinstance(data, TextIOWrapper):
            _data = json.load(data)
        else:
            raise TypeError(f"Requires a string or TextIOWrapper object, not {type(data)}.")
        return cls(_data)

    def to_json(self):
        return json.dumps(self.spec)

    def __str__(self):
        return pformat(self.spec, width=120)


class ComfyApi:
    """
    Api wrapper for ComfyUI.

    - queue_prompt(workflow) -> prompt_id
    - poll(prompt_id)
    - get_output(prompt_id) -> image
    - get_image(filename) -> image
    - put_image(image, filename)

    See scripting examples at
    <https://github.com/comfyanonymous/ComfyUI/tree/master/script_examples>
    """

    def __init__(self, url="http://127.0.0.1:8188"):

        if "://" not in url:
            url = "http://" + url
        parsed_url = urlparse(url)
        # Set default values
        self.protocol = parsed_url.scheme or "http"
        self.host = parsed_url.hostname or "127.0.0.1"
        if parsed_url.port:
            self.port = parsed_url.port
        else:
            # Default port based on the protocol
            self.port = 443 if self.protocol == "https" else 8188
        logger.info(f'setup comfy api {self!r}')

    def endpoint(self, path=""):
        return f"{self.protocol}://{self.host}:{self.port}/{path}"

    def queue_prompt(self, workflow: dict | ComfyWorkflow) -> str:
        if isinstance(workflow, ComfyWorkflow):
            workflow = workflow.spec
        res = requests.post(self.endpoint('prompt'), json={'prompt': workflow})
        prompt_id = res.json().get('prompt_id')
        logger.info(f'submitted prompt {prompt_id}')
        return prompt_id

    def poll_complete(self):

        def executing() -> bool:
            res = requests.get(self.endpoint(f'prompt'))
            # expect response of the form {'exec_info': {'queue_remaining': x}}
            return res.json()['exec_info']['queue_remaining'] != 0

        while executing():
            time.sleep(1.0)

    def get_history(self, prompt_id=None) -> dict:
        endpoint = f"history/{prompt_id}" if prompt_id else "history"
        res = requests.get(self.endpoint(endpoint))
        data = res.json()
        if prompt_id:
            data = data[prompt_id]
        return data

    def get_output(self, prompt_id: str, show=False):
        history = self.get_history(prompt_id)
        output_image_data = []
        pprint( history )
        for node_data in history['outputs'].values():
            if 'images' in node_data:
                for image_data in node_data['images']:
                    if image_data['type'] == "output":
                        output_image_data.append(image_data)
        output_images = []
        for image_data in output_image_data:
            im = self.get_image(**image_data)
            if show:
                im.show()
            output_images.append( im )
        return output_images

    def generate_image(self, workflow: dict | ComfyWorkflow, show=False):
        prompt_id = self.queue_prompt(workflow)
        self.poll_complete()
        output_ims = self.get_output(prompt_id, show)
        return output_ims

    def get_image(self, filename: str, subfolder="", folder_type="output", type=None) -> Image.Image:
        """
        Get a single image by filename, these are also directly accessible via ssh at
        `host:<comfy_dir>/output/<filename>`
        """
        if type:
            folder_type = type
        params = {"filename": filename, "subfolder": subfolder, "type": folder_type}
        res = requests.get(self.endpoint('view'), params=params)
        return Image.open(BytesIO(res.content))

    def put_image(self, im, filename: str, subfolder="", folder_type="input"):
        """
        Put a single image with filename, these are also directly accessible via ssh at
        `host:<comfy_dir>/input/<filename>`
        """
        raise NotImplementedError

    def __repr__(self):
        return f"<{self.__class__.__name__} at {self.endpoint()}>"
