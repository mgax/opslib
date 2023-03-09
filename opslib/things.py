class Thing:
    def __init__(self, **kwargs):
        self._children = {}

    def __setattr__(self, name, value):
        super().__setattr__(name, value)
        if not name.startswith("_") and isinstance(value, Thing):
            self._children[name] = value
            value._attach(self, name)

    def _attach(self, parent, name):
        if hasattr(self, "build"):
            self.build()


class Stack(Thing):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.build()
