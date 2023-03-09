import beartype.door

NO_DEFAULT = object()


class Prop:
    def __init__(self, type, default=NO_DEFAULT):
        self.type = type
        self.default = default


class InstanceProps:
    def __init__(self, cls, kwargs):
        for name in dir(cls.Props):
            prop = getattr(cls.Props, name)
            if not isinstance(prop, Prop):
                continue

            value = kwargs.pop(name, prop.default)

            if value is NO_DEFAULT:
                if not beartype.door.is_bearable(None, prop.type):
                    raise TypeError(f"Required prop {name!r} is missing")

                value = None

            elif not beartype.door.is_bearable(value, prop.type):
                raise TypeError(f"Prop {name!r}: {value!r} is not {prop.type!r}")

            setattr(self, name, value)

        for name in kwargs:
            raise TypeError(f"{name!r} is an invalid prop for {cls!r}")

    def __repr__(self):
        return f"<{type(self).__name__}: {vars(self)}>"
