from functools import cached_property

from .props import InstanceProps


class Meta:
    def __init__(self, thing, name, parent):
        self.thing = thing
        self.name = name
        self.parent = parent

    @cached_property
    def full_name(self):
        if self.parent is None or self.parent._meta.parent is None:
            return self.name

        return f"{self.parent._meta.full_name}.{self.name}"


class Thing:
    class Props:
        pass

    Meta = Meta

    _meta = None

    def __init__(self, **kwargs):
        self._children = {}
        self.props = InstanceProps(self, kwargs)

    def __str__(self):
        return self._meta.full_name if self._meta else "[detached]"

    def __repr__(self):
        return f"<{type(self).__name__} {self}>"

    def __setattr__(self, name, value):
        super().__setattr__(name, value)
        if not name.startswith("_") and isinstance(value, Thing):
            value._attach(self, name)
            self._children[name] = value

    def _attach(self, parent, name):
        if self._meta is not None:
            raise ValueError(
                f"Cannot attach {self!r} to {parent!r} because it's already attached"
            )

        self._meta = self.Meta(thing=self, name=name, parent=parent)
        self.build()

    def __iter__(self):
        return iter(self._children.values())

    def build(self):
        pass


class Stack(Thing):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._meta = self.Meta(thing=self, name="__root__", parent=None)
        self.build()
