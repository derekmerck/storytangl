from collections import UserList
import math

from pydantic import Field, field_validator, ValidationInfo

from .svg_group import SvgGroup

class SvgGroupArray(UserList):
    """
    This is a review tool for generating thumbnails of svg scenes in a regular grid.
    """

    data: list[SvgGroup] = Field(default_factory=list)

    dims: tuple[int, int] = Field(...)

    @field_validator("dims", mode="before")
    def _mk_dims(cls, data, info: ValidationInfo):
        num_groups = len(info.data['data'])
        sqrt = math.sqrt( num_groups )
        w = int( sqrt ) + 1
        h = int( sqrt )
        return w, h

    #: setback to center of each thumbnail, less than 1 overlaps them
    offsets: tuple[float, ...] = (0.5, 0.5)
    #: optional alternating row x offset
    alternating_offset: float = 0.
    #: override bg color
    bgcolor: str = None

    def viewbox(self, source_viewbox: tuple | list) -> tuple:
        viewbox = [*source_viewbox]

        print( viewbox )
        print( self.offsets )
        # put into units
        offsets_ = (self.offsets[0] * viewbox[2],
                    self.offsets[1] * viewbox[3])

        viewbox[0] += offsets_[0] * (0.5)  # back off width
        viewbox[1] += offsets_[1] * (0.1)  # back off height

        # -1 on each margin, -1 for starting 1 to right
        viewbox[2] += offsets_[0] * (max([1, self.dims[0] - 1]))
        viewbox[3] += offsets_[1] * (max([1, self.dims[1] - 1]))

        if self.alternating_offset is not None:
            viewbox[2] += self.alternating_offset * offsets_[0]

        return tuple( viewbox ), offsets_
