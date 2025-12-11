# No longer supported per se

@attr.define(slots=False, hash=False, eq=False)
class PolyRenderable(Renderable):
    # Provides a _desc from a list

    class PickStrategy(Enum):
        RANDOM = "random"
        RANDOM_NO_REPLACE = "random_no_replace"
        ORDERED = "ordered"
        PARENT_CHOICE = "parent_choice"

    descs: List[str] = attr.ib(factory=list)
    pick_by: PickStrategy = attr.ib(default=PickStrategy.RANDOM,
                                    converter=PickStrategy)

    def pick_desc(self, pick_by: PickStrategy = None):
        pick_by_ = pick_by or self.pick_by
        pick_by_ = self.PickStrategy( pick_by_.value )
        if pick_by_ == self.PickStrategy.RANDOM:
            _desc = random.choice(self.descs)
        elif pick_by_ == self.PickStrategy.RANDOM_NO_REPLACE:
            random.shuffle(self.descs)
            _desc = self.descs.pop()
        elif pick_by_ == self.PickStrategy.ORDERED:
            _desc = self.descs.pop(0)
        elif pick_by_ == self.PickStrategy.PARENT_CHOICE:
            # generally this will never be called, parent_choice = ignore pick
            _desc = "\n".join( self.descs )
        else:
            raise RuntimeError(f"No rule for pick_by strategy {self.pick_by}")
        return _desc

    _labels: List[str] = attr.ib( factory=list )
    def label(self, which: int = None, **kwargs) -> str:
        if self._label:
            _label = self._label
        elif not self._labels:
            return
        elif which is not None:
            _label = self._labels[which]
        elif len( self._labels ) == 1:
            _label = self._labels[0]
        else:
            _label = random.choice( self._labels )
        return self._render( _label, **(self.ns() | kwargs) )

    def render_desc(self, ns: Dict):
        desc = self.pick_desc()
        res = Renderable._render( desc, ns )
        return res
