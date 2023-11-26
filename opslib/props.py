import beartype.door

from .lazy import Lazy, evaluate

NO_DEFAULT = object()


class Prop:
    """
    The Prop class is the definition of a component *Prop*. See
    :ref:`component-props`.

    :param type: The :class:`type` that the value must match.
    :param default: Default value if the prop is not specified. Falls back to
                    ``None`` if not specified.
    :param lazy: If ``True``, the value may be :class:`~opslib.lazy.Lazy`, and
                 its type will be checked when it's evaluated.
    """

    remainder = object()

    def __init__(self, type, default=NO_DEFAULT, lazy=False):
        self.type = type
        self.default = default
        self.lazy = lazy

    def wrap_lazy(self, instance, name, lazy_value):
        assert self.lazy
        assert isinstance(lazy_value, Lazy)

        def get_value_and_check():
            value = evaluate(lazy_value)

            if not beartype.door.is_bearable(value, self.type):
                raise TypeError(
                    f"Lazy prop {name!r} for {instance!r}: "
                    f"{value!r} is not {self.type!r}"
                )

            return value

        return Lazy(get_value_and_check)


def get_instance_props(instance, kwargs):
    if instance._props_dataclass:
        return instance._props_dataclass(**kwargs)

    props = {}

    for name, prop in instance.Props.__dict__.items():
        if prop is Prop.remainder:
            props[name] = kwargs
            kwargs = {}
            break

        if not isinstance(prop, Prop):
            continue

        value = kwargs.pop(name, prop.default)
        if prop.lazy and isinstance(value, Lazy):
            value = prop.wrap_lazy(instance, name, value)

        else:
            if value is NO_DEFAULT:
                if not beartype.door.is_bearable(None, prop.type):
                    raise TypeError(f"Required prop {name!r} is missing")

                value = None

            elif not beartype.door.is_bearable(value, prop.type):
                raise TypeError(f"Prop {name!r}: {value!r} is not {prop.type!r}")

        props[name] = value

    for name in kwargs:
        raise TypeError(f"{name!r} is an invalid prop for {instance!r}")

    return InstanceProps(**props)


class InstanceProps:
    """
    The InstanceProps class is a container for instance props (see
    :ref:`component-props`). Typically it's found as the ``.props`` attribute
    of a :class:`~opslib.components.Component` instance. The props themselves
    are attributes of this object.
    """

    def __init__(self, **kwargs):
        for name, value in kwargs.items():
            setattr(self, name, value)

    def __repr__(self):
        return f"<{type(self).__name__}: {vars(self)}>"
