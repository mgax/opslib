class ComponentCallbacks:
    def __init__(self, component, name):
        self.component = component
        self.prop_name = f"_callbacks_{name}"

    def add(self, callback):
        if not hasattr(self.component, self.prop_name):
            setattr(self.component, self.prop_name, [])
        getattr(self.component, self.prop_name).append(callback)

    def invoke(self):
        for callback in getattr(self.component, self.prop_name, []):
            callback()


class Callbacks:
    def __set_name__(self, owner, name):
        self.name = name

    def __get__(self, obj, objtype=None):
        return ComponentCallbacks(obj, self.name)
