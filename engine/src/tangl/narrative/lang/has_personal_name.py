from pydantic import BaseModel, model_validator, Field

from .gens import IsGendered
from .gendered_nominals import gn

class HasPersonalName(BaseModel):
    """
    Follows western naming order

    accepts either:
    - first, last and joins to create a fullname
    - full_name and splits to create first_name and last_name

    provides
    - name: _name if possible, otherwise first_name or titled_name             # least formal
    - titled_name: title + last_name if possible, otherwise title + name       # base
    - titled_full_name: title + full_name if possible, otherwise titled_name   # most formal
    """

    # todo: probably want to integrate this with a nominal "that blonde guy" desc field for pseudo-anonymous ref

    name_: str = Field(None, alias="name")        # preferred name
    first_name: str = None   # given
    last_name: str = None    # surname
    full_name: str = None    # given + surname
    title_: str = Field("mr.", alias="title")      # mr./mrs. x

    @model_validator(mode='after')
    def _infer_name_parts(self):
        match ( self.first_name is not None,
                self.last_name is not None,
                self.full_name is not None):
            case True, True, True:
                pass
            case True, True, False:
                # f and l given, infer un
                self.full_name = f"{self.first_name} {self.last_name}"
            case False, False, True:
                # un given, infer f and l
                self.first_name, *last_names = self.full_name.split()
                self.last_name = " ".join( last_names )
            case _, _, True:
                raise ValueError("Can't set first or last along with full_name")
        if not (self.name_ or self.first_name or self.last_name):
            raise ValueError(
                f"Must have at least one of name, first_name, last_name, or full_name ({self})")
        # otherwise accept the first or last only.
        return self

    @property
    def name(self):
        # preferred name in least to most formal order
        if self.name_:
            return self.name_        # Jack
        elif self.first_name:
            return self.first_name   # Jonathan
        elif self.full_name:
            return self.full_name    # Jonathan Smith
        else:   # must have a last name
            return self.titled_name  # Mr. Smith

    @property
    def title(self: IsGendered):
        return gn( self.title_, self.is_xx ).capitalize()

    @property
    def titled_name(self):
        # Titled name in most to least formal order
        # if they have a full_name, they have a last name
        if self.last_name:
            return f"{self.title} {self.last_name}"
        # can't refer to 'name' in here b/c recursion
        if self.first_name:
            return f"{self.title} {self.first_name}"
        else:   # must have a name_
            return f"{self.title} {self.name_}"

    @property
    def titled_full_name(self):
        # Formal titled full_name in most to least formal order
        if self.full_name:
            return f"{self.title} {self.full_name}"
        return self.titled_name

    def akas(self):
        return { x for x in
                 [ self.name,
                   self.last_name,
                   self.first_name,
                   self.full_name,
                   self.titled_name,
                   self.titled_full_name] if x is not None }

    def goes_by(self, alias: str) -> bool:
        return alias in self.akas()

