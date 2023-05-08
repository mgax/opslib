Building a Stack
================

*The Stack* is the definition of your infrastructure that Opslib will manage.
It's made up of :doc:`components <components>`, with the root component being
an instance of :class:`~opslib.components.Stack`.

.. code-block:: python
    :caption: ``stack.py``

    from opslib import Stack

    stack = Stack(__name__)

Opslib tries to import a module named ``stack`` (which is why our file is
called ``stack.py``). In the module, it looks for an object named ``stack``.

The ``__name__`` argument helps Opslib figure out where the code is defined, so
it can create its ``.opslib`` directory, next to ``stack.py``, to store its
state.

Attaching components
--------------------

To build up the stack, we attach components to it, by setting them as
attributes:

.. code-block:: python

    from pathlib import Path
    from opslib import LocalHost

    stack.host = LocalHost()
    stack.hello = stack.host.file(
        path=Path("/tmp/hello.txt"),
        content="Hello World!\n"
    )

At this point, the ``host`` and ``hello`` components are attached to the stack,
and will be deployed when we run ``opslib - deploy``.

.. code-block:: none

    $ opslib - deploy
    $ cat /tmp/hello.txt
    Hello World!

Defining components
-------------------

Attaching everything to the root stack object doesn't scale much, so we'll want
to organize components into higher level structures:

.. code-block:: python

    from opslib import Component, Prop

    class Bucket(Component):
        class Props:
            host = Prop(LocalHost)
            color = Prop(str)

        def build(self):
            self.file = self.props.host.file(
                path=Path(f"/tmp/{self.props.color}.txt"),
                content=f"A splash of {self.props.color}\n"),
            )

    stack.red = Bucket(host=stack.host, color="red")
    stack.green = Bucket(host=stack.host, color="green")
    stack.blue = Bucket(host=stack.host, color="blue")

The ``Bucket`` component receives two :ref:`Props`: ``host`` and ``color``.

The component's :meth:`~opslib.components.Component.build` method creates
sub-components and attaches them. It's called when the ``Bucket`` component is
attached to something (in our case, the ``stack``).

.. note::

    :meth:`~opslib.components.Component.build` is *not* called when the
    component is created, but rather later, when it's attached. This means that
    a detached component doesn't have any of its child components created and
    attached yet.
