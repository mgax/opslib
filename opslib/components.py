import logging
from functools import cached_property

from .props import InstanceProps
from .state import StateDirectory, default_state_directory

logger = logging.getLogger(__name__)


class Meta:
    statedir = StateDirectory()

    def __init__(self, component, name, parent):
        self.component = component
        self.name = name
        self.parent = parent

    @cached_property
    def full_name(self):
        if self.parent is None or self.parent._meta.parent is None:
            return self.name

        return f"{self.parent._meta.full_name}.{self.name}"

    @cached_property
    def stack(self):
        return self.component if self.parent is None else self.parent._meta.stack


class Component:
    """
    The basic building block to define the stack. See :doc:`components`.
    """

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
        if not name.startswith("_") and isinstance(value, Component):
            if hasattr(self, name) and name not in self._children:
                raise AttributeError(f"{self!r} already has attribute {name!r}")
            super().__setattr__(name, value)
            value._attach(self, name)
            self._children[name] = value

        else:
            super().__setattr__(name, value)

    def _attach(self, parent, name):
        if self._meta is not None:
            raise ValueError(
                f"Cannot attach {self!r} to {parent!r} because it's already attached"
            )

        self._meta = self.Meta(component=self, name=name, parent=parent)
        self.build()

    def __iter__(self):
        return iter(self._children.values())

    def build(self):
        """
        Called when the component is attached to a parent. Override this method
        to add sub-components.
        """

    def add_commands(self, cli):
        """
        Called when the CLI is constructed. Override this method to add custom
        commands.

        :param cli: A :class:`click.Group` that represents the CLI of this
                    component.
        """


class Stack(Component):
    """
    Stack represents the root of the component stack. It behaves like a regular
    :class:`Component`, except that its ``build()`` method is called when it's
    instantiated.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._meta = self.Meta(component=self, name="__root__", parent=None)
        self.build()

    def get_state_directory(self):
        """
        Returns the directory where opslib will keep its state. Defaults to a
        directory named ``.opslib`` in the parent folder of the file where the
        class is defined. Override this method if you want to store state
        elsewhere.
        """

        return default_state_directory(self)


def walk(component):
    """
    Iterate depth-first over all child components. The first item is
    ``component`` itself.
    """

    yield component
    for child in component:
        yield from walk(child)


def init_statedir(stack):
    from .operations import Printer

    for component in walk(stack):
        changed = component._meta.statedir.init()
        if changed:
            Printer(component).print_component(changed=True)
