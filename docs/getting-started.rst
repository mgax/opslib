Getting Started
===============

Project Layout
--------------

Deploying a stack has many moving parts, so it pays to set up the project in a
way that will make life easier in the long run.

Source control
~~~~~~~~~~~~~~

The stack will evolve over time, and it pays to have a history, so let's set up
a Git_ repository:

.. _Git: https://git-scm.com/

.. code-block:: none

    $ git init mystack
    $ cd mystack

Some files should _not_ be tracked in Git history, either because they contain
secrets, or because they contain temporary data, so we create a `.gitignore`
file:

.. code-block:: none
    :caption: ``.gitignore``

    .envrc
    .opslib
    .venv

Python environment
~~~~~~~~~~~~~~~~~~

Create a virtual environment using :mod:`venv`:

.. code-block:: none

    $ python3 -m venv .venv

Direnv for environment variables
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A good many things can be configured through environment variables, so let's
set up direnv_ to manage them. Any time our terminal is inside the project
directory, *direnv* loads environment variables from the file named ``.envrc``.
It's a handy place to activate_ the virtual environment and to configure the
Terraform plugin cache.

.. _direnv: https://direnv.net/
.. _activate: https://docs.python.org/3/library/venv.html#how-venvs-work

.. code-block:: none
    :caption: ``.envrc``

    source .venv/bin/activate
    export TF_PLUGIN_CACHE_DIR=$HOME/.terraform.d/plugin-cache

Since we expect to store secrets in this file, let's restrict its permissions:

.. code-block:: none

    $ chmod 600 .envrc

After any change to ``.envrc`` we must tell *Direnv* that the changes are
intentional:

.. code-block:: none

    $ direnv allow

Installation
------------

.. note::

    Opslib is under heavy development; the GitHub install is the recommended
    option for now.

PyPI
~~~~

Opslib is published to PyPI under the name pyopslib_::

    $ pip install pyopslib

.. _pyopslib: https://pypi.org/project/pyopslib/

GitHub
~~~~~~

Install the current ``main`` branch::

    $ pip install git+https://github.com/mgax/opslib

Editable
~~~~~~~~

If you're working on opslib itself, after you set up the source tree
(see :doc:`contributing`), install the package in "edit" mode::

    $ pip install -e /path/to/opslib

Hello World
-----------

Let's create a minimal stack:

.. code-block:: python
    :caption: ``stack.py``

    from opslib import LocalHost, Stack

    stack = Stack(__name__)
    stack.host = LocalHost()
    stack.hello = stack.host.command(
        args=["echo", "Hello world!"],
    )

Does it work?

.. code-block:: none

    $ opslib - diff
    hello Command [changed]
    1 changed
    <class 'opslib.places.Command'>: 1

    $ opslib - deploy
    hello Command ...
    Hello world!
    hello Command [changed]
    1 changed
    <class 'opslib.places.Command'>: 1

Next Steps
----------

If you're new to Opslib, the :ref:`tutorial` is a great place to start.
