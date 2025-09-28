# tangl.core.fragment.control_fragment.py
from typing import Literal, Optional
from enum import Enum

from pydantic import Field, model_validator

from tangl.type_hints import Identifier, UnstructuredData
from tangl.core.registry import Registry
from .base_fragment import BaseFragment

ControlFragmentType = Literal['update', 'delete']

class ControlFragment(BaseFragment, extra='allow'):
    # a graph item fragment
    fragment_type: ControlFragmentType = 'update'

    reference_type: str | Enum = Field('content', alias='ref_type')
    reference_id: Identifier = Field(..., alias='ref_id')
    # identifier (uid or unique label) for the content fragment that we want to update content or presentation for

    payload: Optional[UnstructuredData] = None

    @model_validator(mode="after")
    def _validate_payload(self):
        if self.record_type == 'update_fragment':
            if self.payload is None:
                raise ValueError('payload cannot be None for an update fragment')
        return self

    def reference(self, registry: Registry[BaseFragment]) -> BaseFragment:
        return registry.find_one(identifier=self.reference_id)
