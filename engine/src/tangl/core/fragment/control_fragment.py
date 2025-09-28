# tangl.core.fragment.control_fragment.py
from typing import Literal, Optional

from pydantic import Field, model_validator

from tangl.type_hints import Identifier, UnstructuredData
from tangl.core import Registry
from tangl.core.record import Record

ControlFragmentType = Literal['update_fragment', 'delete_fragment']

class ControlFragment(Record, extra='allow'):
    # a graph item fragment
    record_type: ControlFragmentType = Field("update_fragment", alias='type')
    reference_type: Literal['content'] = Field("content", alias='ref_type')
    reference_id: Identifier = Field(..., alias='ref_id')
    # identifier (uid or unique label) for the content fragment that we want to update content or presentation for

    payload: Optional[UnstructuredData] = None

    @model_validator(mode="after")
    def _validate_payload(self):
        if self.record_type == 'update_fragment':
            if self.payload is None:
                raise ValueError('payload cannot be None for an update fragment')
        return self

    def reference(self, registry: Registry[Record]) -> Record:
        return registry.find_one(identifier=self.reference_id)
