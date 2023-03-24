Project Layout
==============

Create a directory for the project and enter it, then create a virtualenv:

.. code-block:: none

    $ mkdir my-code-forge
    $ cd my-code-forge
    $ python3 -m venv .venv

To manage the environment, we'll use direnv_, which reads a configuration file
in the current directory, and configures environment variables. Later in the
tutorial, we're going to configure API tokens for cloud services, and we'll set
them as environment variables in the direnv config file.

Create a file named ``.envrc`` with this content:

.. _direnv: https://direnv.net/

.. code-block:: none
    :caption: ``.envrc``

    source .venv/bin/activate

Then approve the direnv configuration and make sure it's not world-readable:

.. code-block:: none

    $ direnv allow
    $ chmod 600 .envrc

Now the virtualenv should be activated automatically any time we are in the
project directory. Time to install opslib as described in
:doc:`../installation`.

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

    from opslib.components import Stack
    from opslib.places import LocalHost

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

Lines 1 and 3 show us which component is being deployed. Line 2 is the
command's output. The last two lines are a summary of what happened.

Continue to :doc:`local`.
