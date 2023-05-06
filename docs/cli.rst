Command-line interface
======================

Opslib provides a powerful command-line interface to operate on the
infrastructure. Besides the basic deployment operations, it allows direct
interaction with components, and defining custom commands.

Argument structure
------------------

Unlike most shell commands, which follow an *<executable> <command> <target>*
structure, ``opslib`` expects *<executable> <target> <command>*, because the
available commands are different depending on the target.

The first argument is the dotted name of the target component. Therefore, can
run commands on any component in the stack.

.. code-block:: python
    :caption: stack.py

    from opslib.components import Component, Stack

    def get_stack():
        stack = Stack()
        stack.foo = Component()
        stack.foo.bar = Component()

With the stack defined above, we can run the ``id`` command (which simply
prints the :func:`repr` of the target) on the ``bar`` component:

.. code-block:: none

    $ opslib foo.bar id
    <Component foo.bar>

We can also specify ``-`` as a target. It will select the root element, the
stack itself:

.. code-block:: none

    $ opslib - id
    <Stack __root__>

Most of the examples below will target the whole stack, but any command can be
run on any component in the stack, so you can for example do a partial deploy.

Checking differences
--------------------

Before applying actual changes to infrastructure, it's a good idea to check what is going to happen. We can run ``diff`` to see.

.. code-block:: none

    $ opslib - diff
    [...]
    app.app_py.action AnsibleAction [changed]
    --- /opt/prj/opslib/examples/compose/target/opslib-examples-compose/app.py
    +++ /opt/prj/opslib/examples/compose/target/opslib-examples-compose/app.py
    @@ -5,4 +5,4 @@

     @app.route("/")
     def hello_world():
    -    return "<p>Hello, World!</p>"
    +    return "<p>Hello, World! Changes are afoot.</p>"

    app.compose_file.action AnsibleAction [ok]
    [...]
    9 ok
    1 changed
    <class 'opslib.ansible.AnsibleAction'>: 1

.. note::

    Some components, e.g. :class:`~opslib.places.File`, cache the fact that
    they have been deployed successfully. If the remote file is changed, opslib
    won't pick up the change, unless you run *refresh*.

    If, however, the component props change, opslib will pick up the
    difference, and will update the remote file.

Refreshing local state
----------------------

Sometimes the infrastructure changes and opslib needs to update its state. This
is done with the ``refresh`` command:

.. code-block:: none

    opslib - refresh

Deploying
---------

The ``deploy`` command visits each component in sequence, depth-first, and
performs some specific action on the infrastructure. The action depends on the
type of component; it may be creating a directory or writing a file, or
spinning up a VM.

Components are visited in the order they are attached to their parent. If the
application of a component fails, the process stops.

.. code-block:: none

    opslib - deploy

Defining custom commands
------------------------

Sometimes it helps to provide special commands on a component. For example, a
component representing a `Docker Compose`_ project might define a ``compose``
command that executes ``docker compose`` in the context of the project. Or a
component implementing a systemd unit might define a ``systemctl`` command that
runs *systemctl* with that unit as first argument.

When the CLI for a component is invoked, opslib prepares a :class:`click.Group`
object, that implements the component's CLI. It adds the default commands for
``deploy``, ``diff``, etc. It then calls
:meth:`~opslib.components.Component.add_commands` with a single argument, the
*click.Group* object, so you can attach additional commands. Refer to the
`Click documentation`_ for details on implementing commands.

.. _Click documentation: https://click.palletsprojects.com

.. code-block:: python

    import click
    from opslib.components import Component

    class MyComponent(Component):
        def add_commands(self, cli):
            @cli.command()
            @click.argument("message")
            def speak(message):
                click.echo(click.style(message, fg="red"))

.. _Docker Compose: https://docs.docker.com/compose/
