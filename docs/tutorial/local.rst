Local Deployment
================

Time to actually deploy something! Here we create a docker-compose
configuration for Gitea and deploy it locally.

Adding Gitea to the stack
-------------------------

The Gitea definition is big enough to warrant its own Python file which will be
``stack/gitea.py``.

First we generate a ``docker-compose.yml`` file, along with its project
directory, and a data volume.

.. code-block:: python
    :caption: ``stack/gitea.py``

    import yaml

    from opslib.components import Component
    from opslib.places import Directory
    from opslib.props import Prop


    class Gitea(Component):
        class Props:
            directory = Prop(Directory)
            listen = Prop(str)

        def build(self):
            self.directory = self.props.directory
            self.data_volume = self.directory / "data"

            self.compose_file = self.directory.file(
                name="docker-compose.yml",
                content=self.compose_file_content,
            )

        @property
        def compose_file_content(self):
            content = dict(
                version="3",
                services=dict(
                    app=dict(
                        image="gitea/gitea:1.19.0",
                        volumes=[
                            f"{self.data_volume.path}:/data",
                        ],
                        restart="unless-stopped",
                        ports=[
                            f"{self.props.listen}:3000",
                        ],
                    ),
                ),
            )
            return yaml.dump(content, sort_keys=False)

Then, in ``stack/__init__.py``, we import and instantiate it:

.. code-block:: python
    :caption: ``stack/__init__.py``

    from pathlib import Path
    from opslib.components import Stack
    from opslib.places import LocalHost
    from .gitea import Gitea

    class MyCodeForge(Stack):
        def build(self):
            host = LocalHost()
            target_path = Path(__file__).parent.parent / "target"
            self.directory = host.directory(target_path)
            self.gitea = Gitea(
                directory=self.directory / "gitea",
                listen="3000",
            )

    def get_stack():
        return MyCodeForge()

Quite a few things going on here! Let's take them one at a time.

Components and Props
^^^^^^^^^^^^^^^^^^^^

Our stack is made up of :class:`~opslib.components.Component` objects. They are
the universal building block: Ansible actions, Terraform resources, shell
commands, and your own infrastructure components. They are composable and
hierarchical.

Each Component may receive :class:`Props <opslib.props.Prop>`, which configure
it, and inject dependencies. Props are typed and available as ``self.props`` in
the instance.

The :meth:`~opslib.components.Component.build` method is called when a
Component instance is created. It can add child components to the instance and
do any needed setup.

Places
^^^^^^

Hosts, directories and files are the bread and butter of deployment. Here we
use :class:`~opslib.places.LocalHost` because we're deploying locally, but the
same code will work unchanged when we'll want to deploy to a remote host over
SSH.

By setting the :class:`~opslib.places.Directory` objects ``self.directory`` and
``self.data_volume`` on the ``Gitea`` instance, we attach them to our stack,
which ensures the directories will be created.

Deploying the Stack
-------------------

Opslib will create a subdirectory named ``.opslib`` in our project where it will
keep track, among other things, of which components got deployed successfully.
It's useful to assume that files don't change by themselves after we write
them, so that we skip them, and the deployment process is quicker.

.. note::

    Reality is not so simple; remote state will change behind our backs. The
    ``refresh`` command will update local state to reflect reality.

Dry-run deployment aka diff
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Before making changes to sensitive infrastructure, it's a good idea to first
perform a dry-run. The ``diff`` command will show what is going to change:

.. code-block:: none

    $ opslib - diff
    gitea.directory.action AnsibleAction [changed]
    gitea.data_volume.action AnsibleAction [changed]
    gitea.compose_file.action AnsibleAction [changed]
    --- /opt/prj/opslib/examples/tutorial/target/gitea/docker-compose.yml
    +++ /opt/prj/opslib/examples/tutorial/target/gitea/docker-compose.yml
    @@ -0,0 +1,9 @@
    +version: '3'
    +services:
    +  app:
    +    image: gitea/gitea:1.19.0
    +    volumes:
    +    - /opt/prj/opslib/examples/tutorial/target/gitea/data:/data
    +    restart: unless-stopped
    +    ports:
    +    - 127.0.0.1:3000:3000

    3 changed
    <class 'opslib.ansible.AnsibleAction'>: 3

Actually deploying
^^^^^^^^^^^^^^^^^^

Now for the real deal:

   .. code-block:: none

    $ opslib - diff

The output will be simiar to ``diff``, and will create the compose project in
``target/gitea``.

Running Commands
----------------

Each :class:`~opslib.places.Directory` has a ``host`` property which is a
reference to its parent host. The host has a
:meth:`~opslib.places.LocalHost.run` method, which is a thin wrapper around
``subprocess.run``. Let's add a command to the end of the ``build()`` method of
``Gitea`` that runs ``docker compose up -d``:

.. code-block:: python
    :caption: ``stack/gitea.py``

    class Gitea(Component):
        # ...

        def build(self):
            # ...

            self.compose_up = self.directory.host.command(
                args=[*self.compose_args, "up", "-d"],
            )

        @property
        def compose_args(self):
            return ["docker", "compose", "--project-directory", self.directory.path]

Then run ``diff`` again:

.. code-block:: none

    $ opslib - diff
    gitea.directory.action AnsibleAction [ok]
    gitea.data_volume.action AnsibleAction [ok]
    gitea.compose_file.action AnsibleAction [ok]
    gitea.compose_up Command [changed]
    3 ok
    1 changed
    <class 'opslib.places.Command'>: 1

The first 3 items are directories and files that we've deployed previously, and
they have not changed, so they show up as ``[ok]``. The command, however, will
be run.

.. code-block:: none

    $ opslib - deploy
    gitea.directory.action AnsibleAction [ok]
    gitea.data_volume.action AnsibleAction [ok]
    gitea.compose_file.action AnsibleAction [ok]
    gitea.compose_up Command ...
    [+] Running 2/2
     ⠿ Network gitea_default  Created                        0.0s
     ⠿ Container gitea-app-1  Started                        0.2s
    gitea.compose_up Command [changed]
    3 ok
    1 changed
    <class 'opslib.places.Command'>: 1

If all goes well, Docker will start the gitea container, and you can see it at
http://localhost:3000.

Custom Commands
^^^^^^^^^^^^^^^

Besides opslib's builtin CLI commands, we can define our own, by implementing
:meth:`~opslib.components.Component.add_commands`. We define the ``compose``
command, such named because Click picks up the command name from the function
name; it will run any ``docker compose`` subcommand we ask it.

The host's :meth:`~opslib.places.LocalHost.run` method will normally capture
output and wrap the result in an object, suitable for the deployment machinery.
But we can run commands interactively, by disabling ``capture_output``. We also
set ``exit=True``, which makes Python exit with the same code as the command
that was run, and does not generate a stack trace on error.

.. code-block:: python
    :caption: ``stack/gitea.py``

    import click
    # ...

    class Gitea(Component):
        # ...

        def add_commands(self, cli):
            @cli.command(context_settings=dict(ignore_unknown_options=True))
            @click.argument("args", nargs=-1, type=click.UNPROCESSED)
            def compose(args):
                """Run `docker compose` with the given arguments"""
                self.directory.host.run(
                    *[*self.compose_args, *args],
                    capture_output=False,
                    exit=True,
                )

You'll notice that all the commands so far had ``-`` as first argument. It
means "the root stack object". In fact, the argument is a dotted path in the
stack hierarchy, and can reference any Component in our stack.

.. code-block:: none

    $ opslib gitea compose --help
    Usage: opslib compose [OPTIONS] [ARGS]...

      Run `docker compose` with the given arguments

    Options:
      --help  Show this message and exit.


Let's call our ``compose`` command and give it the ``logs`` subcommand of
``docker compose``:

.. code-block:: none

    $ opslib gitea compose logs --tail=3
    +/bin/zsh:1> cd /opt/prj/opslib/examples/tutorial/target/gitea
    +/bin/zsh:1> docker compose logs '--tail=3'
    gitea-app-1  | 2023/03/20 17:25:56 cmd/web.go:220:listen() [I] [64189724] Listen: http://0.0.0.0:3000
    gitea-app-1  | 2023/03/20 17:25:56 cmd/web.go:224:listen() [I] [64189724] AppURL(ROOT_URL): http://localhost:3000/
    gitea-app-1  | 2023/03/20 17:25:56 ...s/graceful/server.go:62:NewServer() [I] [64189724] Starting new Web server: tcp:0.0.0.0:3000 on PID: 18

This is quite a powerful way of interacting with our deployed resources,
without explicitly shelling into remote hosts, changing directories, etc.

Tear-down the local stack
^^^^^^^^^^^^^^^^^^^^^^^^^

Now that we see it works locally, we can stop the local Gitea, because we'll
deploy it to a VPS.

.. code-block:: none

    $ opslib gitea compose down

Continue to :doc:`vps`.
