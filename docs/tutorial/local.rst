Local Deployment
================

Time to actually deploy something! Here we create a docker-compose
configuration for Gitea and deploy it locally.

Adding Gitea to the stack
-------------------------

First we generate a ``docker-compose.yml`` file, along with its project
directory, and a data volume.

.. code-block:: python
    :caption: ``stack.py``

    from pathlib import Path

    import yaml

    from opslib.places import Directory, LocalHost
    from opslib.props import Prop
    from opslib.things import Stack, Thing


    class Gitea(Thing):
        class Props:
            directory = Prop(Directory)

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
                            "127.0.0.1:3000:3000",
                        ],
                    ),
                ),
            )
            return yaml.dump(content, sort_keys=False)


    class MyCodeForge(Stack):
        def build(self):
            host = LocalHost()
            repo = host.directory(Path(__file__).parent)

            self.gitea = Gitea(
                directory=repo / "localgitea",
            )


    def get_stack():
        return MyCodeForge()

Quite a few things going on here! Let's take them one at a time.

Things and Props
^^^^^^^^^^^^^^^^

Our stack is made up of ``Thing`` objects. They are the universal building
block: Ansible actions, Terraform resources, shell commands, and your own
infrastructure components. They are composable and hierarchical.

Each Thing may receive ``Props``, which configure it, and inject dependencies.
Props are typed and available as ``self.props`` in the instance.

The ``build`` method is called when a Thing instance is created. It can add
child Things to the instance and do any needed setup.

Places
^^^^^^

Hosts, directories and files are the bread and butter of deployment. Here we
use ``LocalHost`` because we're deploying locally, but the same code will work
unchanged when we'll want to deploy to a remote host over SSH.

By setting the ``Directory`` things ``self.directory`` and ``self.data_volume``
on the ``Gitea`` instance, we attach them to our stack, which ensures the
directories will be created.

Deploying the Stack
-------------------

First, we must run the ``init`` command, to initialize the opslib state.

.. code-block:: none

    $ opslib - init

It will create a subdirectory named ``.opslib`` in our project where it will
keep track, among other things, of which things got deployed successfully. It's
useful to assume files don't change by themselves after we write them so that
the deployment process is quick.

.. note::

    Reality is not so simple; remote state will change behind our backs. The
    ``refresh`` command will update local state to reflect reality.

Dry-run deployment aka diff
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Before making changes to sensitive infrastructure, it's a good idea to run a
dry-run first. The ``diff`` command will show what is going to change:

.. code-block:: none

    $ opslib - diff
    gitea.directory.action AnsibleAction [changed]
    gitea.data_volume.action AnsibleAction [changed]
    gitea.compose_file.action AnsibleAction [changed]
    --- /opt/prj/demo/my-code-forge/localgitea/docker-compose.yml
    +++ /opt/prj/demo/my-code-forge/localgitea/docker-compose.yml
    @@ -0,0 +1,9 @@
    +version: '3'
    +services:
    +  app:
    +    image: gitea/gitea:1.19.0
    +    volumes:
    +    - /opt/prj/demo/my-code-forge/localgitea/data:/data
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

The output will be simiar to ``diff``, and will create a file named
``localgitea/docker-compose.yml``.

Running Commands
----------------

Each ``Directory`` has a ``host`` property which is a reference to its parent
host. The host has a ``run`` method, which is a thin wrapper around
``subprocess.run``. Let's add a command to the end of the ``build`` method of
``Gitea`` that runs ``docker compose up -d``:

.. code-block:: python
    :caption: ``stack.py``

    class Gitea(Thing):
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
     ⠿ Network localgitea_default  Created                                                                            0.0s
     ⠿ Container localgitea-app-1  Started                                                                            0.2s
    gitea.compose_up Command [changed]
    3 ok
    1 changed
    <class 'opslib.places.Command'>: 1

If all goes well, Docker will start the gitea container. You can now open
http://localhost:3000 in your browser and finish the Gitea installation by
scrolling to the bottom and clicking "Install Gitea". Then click on "Need an
account? Register now."; the first account will be an admin.

Custom Commands
^^^^^^^^^^^^^^^

Besides opslib's builtin CLI commands, we can define our own, by implementing
``add_commands``. We define the ``compose`` command, such named because Click
picks up the command name from the function name; it will run any ``docker
compose`` subcommand we ask it.

The host's ``run`` method will normally capture output and wrap the result in
an object, suitable for the deployment machinery. But we can run commands
interactively, by disabling ``capture_output``. We also set ``exit=True``,
which makes Python exit with the same code as the command that was run, and
does not generate a stack trace on error.

.. code-block:: python
    :caption: ``stack.py``

    import click
    # ...

    class Gitea(Thing):
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
stack hierarchy, and can reference any Thing in our stack.

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
    +/bin/zsh:1> cd /opt/prj/demo/my-code-forge/localgitea
    +/bin/zsh:1> docker compose logs '--tail=3'
    localgitea-app-1  | 2023/03/20 17:25:56 cmd/web.go:220:listen() [I] [64189724] Listen: http://0.0.0.0:3000
    localgitea-app-1  | 2023/03/20 17:25:56 cmd/web.go:224:listen() [I] [64189724] AppURL(ROOT_URL): http://localhost:3000/
    localgitea-app-1  | 2023/03/20 17:25:56 ...s/graceful/server.go:62:NewServer() [I] [64189724] Starting new Web server: tcp:0.0.0.0:3000 on PID: 18

This is quite a powerful way of interacting with our deployed resources,
without explicitly shelling into remote hosts, changing directories, etc.
