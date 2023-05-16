import logging
import sys
from functools import cached_property
from pathlib import Path

from .props import InstanceProps
from .state import StateDirectory

logger = logging.getLogger(__name__)


class Meta:
    statedir = StateDirectory()

    def __init__(self, component, name, parent, stateroot=None):
        self.component = component
        self.name = name
        self.parent = parent
        self.stateroot = stateroot

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

        :param cli: A :class:`~opslib.cli.ComponentGroup` that represents the
                    CLI of this component.
        """


def get_stateroot(import_name):
    module = sys.modules[import_name]
    return Path(module.__file__).parent / ".opslib"


class Stack(Component):
    def __init__(self, import_name=None, stateroot=None, **kwargs):
        if import_name is None and stateroot is None:
            raise ValueError("Either `import_name` or `stateroot` must be set")

        super().__init__(**kwargs)

        self._meta = self.Meta(
            component=self,
            name="__root__",
            parent=None,
            stateroot=stateroot or get_stateroot(import_name),
        )
        self.build()


def walk(component):
    """
    Iterate depth-first over all child components. The first item is
    ``component`` itself.
    """

    yield component
    for child in component:
        yield from walk(child)
