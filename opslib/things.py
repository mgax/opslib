from .props import InstanceProps


class Thing:
    class Props:
        pass

    def __init__(self, **kwargs):
        self._children = {}
        self.props = InstanceProps(self, kwargs)

    def __setattr__(self, name, value):
        super().__setattr__(name, value)
        if not name.startswith("_") and isinstance(value, Thing):
            value._attach(self, name)
            self._children[name] = value

    def _attach(self, parent, name):
        if hasattr(self, "build"):
            self.build()


class Stack(Thing):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.build()
