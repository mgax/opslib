Project Layout
==============

Create a directory for the project and enter it:

.. code-block:: none

    $ mkdir my-code-forge
    $ cd my-code-forge

Set up a virtualenv and install opslib:

.. code-block:: none

    $ python3 -m venv .venv
    $ source .venv/bin/activate
    $ pip install git+https://github.com/mgax/opslib

Any opslib project contains a *stack* which describes the infrastructure. By
default, opslib tries to import the ``stack`` module or package, and expects a
``get_stack`` factory function.

Our project will be spread over several Python files so we'll organise them in
a package:

.. code-block:: none

    $ mkdir stack

Let's create a simple stack in the package's ``__init__.py`` file:

.. code-block:: python
    :caption: ``stack/__init__.py``

    from opslib.places import LocalHost
    from opslib.things import Stack

    class MyCodeForge(Stack):
        def build(self):
            host = LocalHost()
            self.speak = host.command(
                args=["echo", "Hello World!"],
            )

    def get_stack():
        return MyCodeForge()

This stack runs a single command which prints a message. Let's deploy it:

.. code-block:: none

    $ opslib - deploy
    speak Command ...
    Hello World!
    speak Command [changed]
    1 changed
    <class 'opslib.places.Command'>: 1

Lines 1 and 3 show us which thing is being deployed. Line 2 is the command's
output. The last two lines are a summary of what happened.

Continue to :doc:`local`.
