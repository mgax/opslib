from functools import cached_property, wraps
from typing import TypeVar


class NotAvailable(KeyError):
    """
    The NotAvailable exception indicates that the requested :class:`Lazy` value
    depends on some data that is not available at this time.
    """


T = TypeVar("T")


class Lazy[T]:
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
    def value(self) -> T:
        """
        When ``value`` is retrieved, the Lazy object evaluates itself and
        returns the result.
        """

        return self.func(*self.args, **self.kwargs)


MaybeLazy = Lazy[T] | T


def evaluate(ob: MaybeLazy[T]) -> T:
    """
    Evaluate :class:`Lazy` objects and return the result. If invoked with a
    non-*Lazy* argument, it traverses nested lists and dictionaries, making
    copies of them, and evaluating any *Lazy* values inside.
    """

    if isinstance(ob, Lazy):
        return ob.value

    if isinstance(ob, dict):
        return {k: evaluate(v) for k, v in ob.items()}  # type: ignore

    if isinstance(ob, list):
        return [evaluate(i) for i in ob]  # type: ignore

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
