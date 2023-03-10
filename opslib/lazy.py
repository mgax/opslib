from functools import cached_property, wraps


class Lazy:
    def __init__(self, func, *args, **kwargs):
        self.func = func
        self.args = args
        self.kwargs = kwargs

    @cached_property
    def value(self):
        return self.func(*self.args, **self.kwargs)


def is_lazy(ob):
    return isinstance(ob, Lazy)


def evaluate(ob):
    if is_lazy(ob):
        return ob.value

    if isinstance(ob, dict):
        return {k: evaluate(v) for k, v in ob.items()}

    if isinstance(ob, list):
        return [evaluate(i) for i in ob]

    return ob


def lazy_property(func):
    @property
    @wraps(func)
    def getter(self):
        def wrapper():
            return func(self)

        return Lazy(wrapper)

    return getter
