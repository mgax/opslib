Components
==========

Opslib defines infrastructure in terms of :class:`Components
<opslib.components.Component>`. They encapsulate a particular slice of
infrastructure, and are typically built from smaller components. They are
reusable, and configured via :class:`Props <opslib.props.Prop>`.


Build
-----

A typical component will have a :meth:`~opslib.components.Component.build`
method which defines its structure:

.. code-block:: python

    from opslib.components import Component, Stack
    from opslib.places import LocalHost

    class Cat(Component):
        def build(self):
            self.speak = LocalHost().command(
                args=["echo", "meow"],
            )

    class House(Component):
        def build(self):
            self.spot = Cat()
            self.oscar = Cat()

    stack = Stack()
    stack.apartment = House()

By setting ``self.spot`` and ``self.oscar``, we attach the ``Cat`` instances to
the ``House`` instance, thus adding them to our stack. The ``Cat`` instances
take their names from the attribute names: ``spot`` and ``oscar``.

Components know their place in the stack. For instance, calling :class:`str()
<str>` or :func:`print` on them yields their full path. Calling :func:`repr`
also yields the class name:

.. code-block:: python

    >>> print(stack.apartment.spot)
    apartment.spot
    >>> print(repr(stack.apartment.spot))
    <Cat apartment.spot>

Components can also enumerate their children if we iterate over them:

.. code-block:: python

    >>> print(list(stack))
    [<House apartment>]
    >>> print(list(stack.apartment))
    [<Cat apartment.spot>, <Cat apartment.oscar>]

The ``build()`` method is actually called on child components as a result of
attaching them to their parent. The exception is the
:class:`~opslib.components.Stack` class; its ``build()`` method gets called
during ``__init__``.

.. _component-props:

Props
-----

A component expects its configuration to be supplied via named :class:`Props
<opslib.props.Prop>`.

.. code-block:: python

    from opslib.components import Component
    from opslib.places import LocalHost
    from opslib.props import Prop

    class Cat(Component):
        class Props:
            color = Prop(str)
            energy = Prop(int, default=2)

The ``Cat`` component above expects a ``color`` prop, which must be a string,
and an integer ``energy`` prop, which, if missing, defaults to ``2``.

Consuming props
~~~~~~~~~~~~~~~

When the component is instantiated, its keyword arguments are turned into
props, and set as ``self.props``:

.. code-block:: python

    class Cat(Component):
        class Props:
            color = Prop(str)
            energy = Prop(int, default=2)

        def build(self):
            if self.props.energy > 5:
                self.play = LocalHost().command(
                    args=["echo", f"You see a blur of {self.props.color}."],
                )

.. code-block:: python

    >>> stack = Stack()
    >>> stack.spot = Cat(color="orange", energy=11)
    >>> print(stack.spot.props)
    <InstanceProps: {'color': 'orange', 'energy': 11}>
    >>> print(stack.spot.play.run().output)
    You see a blur of orange.

    >>> stack.oscar = Cat(color="orange")
    >>> print(stack.oscar.props)
    <InstanceProps: {'color': 'orange', 'energy': 2}>
    >>> print(stack.oscar.play.run().output)
    AttributeError: 'Cat' object has no attribute 'play'

Oscar doesn't have the ``play`` attribute because he's too sleepy.

Lazy values
-----------

Sometimes a value is not available when a component is defined. It might depend
on another component that will be defined later, or on remote state. The
:class:`~opslib.lazy.Lazy` class wraps such values, and the
:func:`~opslib.lazy.evaluate` function unwraps them. Multiple calls of
``evaluate`` on the same lazy value will result in a single evaluation; the
result is cached.

.. code-block:: python

    from opslib.lazy import Lazy, evaluate

    def get_value():
        print("get_value was called")
        return "meow"

    print("Preparing a lazy value")
    cat = Lazy(get_value)
    print("Evaluating ...")
    value = evaluate(cat)
    print("Value is", value)

This should output:

.. code-block:: none

    Preparing a lazy value
    Evaluating ...
    get_value was called
    Value is meow

Component props will accept lazy values if they are defined with ``lazy=True``.
If so, the lazy object is wrapped again, and its type is checked when it's
evaluated.
