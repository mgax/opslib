from functools import cached_property, wraps


class NotAvailable(KeyError):
    """
    The NotAvailable exception indicates that the requested :class:`Lazy` value
    depends on some data that is not available at this time.
    """


class Lazy:
    """
    A Lazy object wraps a value that will be available at a later time.

    When evaluated, it invokes its arguments as ``func(*args, **kwargs)``,
    caches the result and returns it.
    """

    def __init__(self, func, *args, **kwargs):
        self.func = func
        self.args = args
        self.kwargs = kwargs

    @cached_property
    def value(self):
        """
        When ``value`` is retrieved, the Lazy object evaluates itself and
        returns the result.
        """

        return self.func(*self.args, **self.kwargs)


def is_lazy(ob):
    return isinstance(ob, Lazy)


def evaluate(ob):
    """
    Evaluate :class:`Lazy` objects and return the result. If invoked with a
    non-*Lazy* argument, it traverses nested lists and dictionaries, making
    copies of them, and evaluating any *Lazy* values inside.
    """

    if is_lazy(ob):
        return ob.value

    if isinstance(ob, dict):
        return {k: evaluate(v) for k, v in ob.items()}

    if isinstance(ob, list):
        return [evaluate(i) for i in ob]

    return ob


def lazy_property(func):
    """
    Similar to :class:`@property <property>`, makes a method function like an instance
    property. When the property is retrieved, it returns a :class:`Lazy`
    object, that invokes the method when evaluated.
    """

    @cached_property
    @wraps(func)
    def getter(self):
        def wrapper():
            return func(self)

        return Lazy(wrapper)

    return getter
