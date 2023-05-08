Places: provisioning hosts
==========================

The :mod:`opslib.places` module defines components for provisioning resources
inside hosts. They are used to set up configuration files, scripts, and run
commands.

Hosts
-----

:class:`~opslib.places.LocalHost` represents the local host where Opslib is
run. :class:`~opslib.places.SshHost` represents a host that can be accessed
over SSH. Both inherit from :class:`~opslib.places.BaseHost`.

The host components don't actually deploy anything. They are needed by other
components to tell them where to operate, and provide handy factory methods to
create them.

.. code-block:: python

    from opslib import LocalHost, Stack

    stack = Stack(__name__)
    stack.host = LocalHost()

Directories and Files
---------------------

:class:`~opslib.places.Directory` represents a directory in a particular host.
During deployment it gets created and optionally a permissions mode is set.

.. code-block:: python

    from pathlib import Path
    from opslib import Directory

    stack.directory = Directory(
        host=stack.host,
        path=Path("/opt/opslib"),
    )

Using the shorthand :meth:`~opslib.places.BaseHost.directory` method, this is
equivalent:

.. code-block:: python

    stack.directory = stack.host.directory("/opt/opslib")

The directory also has a convenience :meth:`~opslib.places.Directory.subdir`
method to create a subdirectory, which is also aliased to the ``/`` operator:

.. code-block:: python

    stack.appdir = stack.directory.subdir("app")
    stack.appdir = stack.directory / "app"

:class:`~opslib.places.File` represents a file on a particular host.

.. code-block:: python

    stack.hello_txt = File(
        host=stack.host,
        path=Path("/opt/opslib/app/hello.txt"),
        content="Hello World!\n",
    )

The :meth:`BaseHost.file() <opslib.places.BaseHost.file>` and
:meth:`Directory.file() <opslib.places.Directory.file>` methods can be used as
shorthand; the latter in particular makes for terse code that doesn't repeat
directory paths much:

.. code-block:: python

    stack.hello_txt = stack.host.file(
        path=Path("/opt/opslib/app/hello.txt"),
        content="Hello World!\n",
    )

    stack.hello_txt = stack.appdir.file(
        name="hello.txt",
        content="Hello World!\n",
    )

Commands
--------

:class:`~opslib.places.Command` will run a command on a particular host upon
deployment.

.. code-block:: python

    from textwrap import dedent
    from opslib import LocalHost, Stack

    stack = Stack(__name__)
    stack.host = LocalHost()
    stack.directory = stack.host.directory("/opt/opslib/app")
    stack.compose_file = stack.directory.file(
        name="docker-compose.yml",
        content=dedent(
            """\
            version: "3"
            services:
              app:
                image: nginx
                ports:
                  - 8080:80
            """
        ),
    )

    compose_args = ["docker", "compose", "--project-directory", stack.directory.path]
    stack.compose_up = stack.host.command(
        args=[*self.compose_args, "up", "-d", "-t1"],
    )

This will run ``docker compose up -d``, in the directory ``/opt/opslib/app``,
on each deployment.

If the ``run_after`` prop is set, the command will only run after one of the
listed components is deployed and reports that it changed:

.. code-block:: python

    stack.compose_up = stack.host.command(
        args=[*self.compose_args, "up", "-d", "-t1"],
        run_after=[stack.compose_file],
    )

Defined like this, the ``compose_up`` command will only run after
``docker-compose.yml`` is changed.
