Local Deployment
================

The goal here is to deploy Gitea_ in a `Docker Compose`_ stack on the local
machine. It will listen on port 3000 and is a stepping stone to deploying in
the cloud.

.. _Gitea: https://gitea.io/
.. _Docker Compose: https://docs.docker.com/compose/

It's assumed that you've already created a project as described in
:ref:`Getting Started`. In particular, we'll need *direnv* to set environment
variables later on.

Minimalist Compose Stack
------------------------

Let's begin with a minimalist stack that simply creates a
``docker-compose.yml`` file and then runs ``docker compose up -d``. Copy the
following to ``stack.py``:

.. code-block:: python
    :caption: ``stack.py``

    from pathlib import Path
    from opslib import LocalHost, Stack

    COMPOSE_YML = """\
    version: "3"
    services:
      app:
        image: gitea/gitea:1.19.0
        volumes:
          - ./data:/data
        restart: unless-stopped
        ports:
          - 127.0.0.1:3000:3000
    """

    stack = Stack(__name__)
    stack.host = LocalHost()
    stack.directory = stack.host.directory(Path(__file__).parent / "target")

    stack.compose_file = stack.directory.file(
        name="docker-compose.yml",
        content=COMPOSE_YML,
    )

    stack.compose_up = stack.directory.command(
        args=["docker", "compose", "up", "-d"],
    )

The stack is made up of 4 components:

* *stack.host* is a :class:`~opslib.places.LocalHost`. It doesn't deploy
  anything but it's a starting point to define other components.
* *stack.directory* is a :class:`~opslib.places.Directory` named ``target``.
* *stack.compose_file* is a :class:`~opslib.places.File`, with its contents
  coming from ``COMPOSE_YML`` defined above. Because it's created from
  *stack.directory*, it will be deployed inside that directory.
* *stack.compose_up* is a :class:`opslib.places.Command` that will be run upon
  deployment. Because it, too, is created from *stack.directory*, it will run
  inside that directory. It starts up the compose service.

Components are :ref:`attached to the stack <Attaching components>` by setting
them as attributes of the :class:`~opslib.components.Stack` instance (or indeed
to other components). The name of the attribute is used as the name of the
component.

When you deploy the stack, each component is deployed, in sequence:

.. code-block:: none

    $ opslib - deploy
    directory.action AnsibleAction [changed]
    compose_file.action AnsibleAction [changed]
    --- /opt/prj/opslib/examples/tutorial-minimal/target/docker-compose.yml
    +++ /opt/prj/opslib/examples/tutorial-minimal/target/docker-compose.yml
    @@ -0,0 +1,9 @@
    +version: "3"
    +services:
    +  app:
    +    image: gitea/gitea:1.19.0
    +    volumes:
    +      - ./data:/data
    +    restart: unless-stopped
    +    ports:
    +      - 127.0.0.1:3000:3000

    compose_up Command ...
    [+] Running 2/2
     ✔ Network target_default  Created                              0.0s
     ✔ Container target-app-1  Started                              0.5s
    compose_up Command [changed]
    3 changed
    <class 'opslib.ansible.AnsibleAction'>: 2
    <class 'opslib.places.Command'>: 1

If the command completes successfully, go to http://localhost:3000/, you should
see Gitea's initial setup screen.

Refactor the stack using components
-----------------------------------

The stack above works, but is not super flexible. For example, we might want to
deploy two instances of the application (local and in the cloud), with slightly
different configuration. So the next step is to refactor the Gitea application
into a :ref:`Component <Components>`.

Create a file ``gitea.py`` with the following content:

.. code-block:: python
    :caption: ``gitea.py``

    import yaml
    from opslib import Component, Directory, Prop


    class Gitea(Component):
        class Props:
            directory = Prop(Directory)
            listen = Prop(str)

        def build(self):
            self.directory = self.props.directory
            self.compose_file = self.directory.file(
                name="docker-compose.yml",
                content=self.compose_content,
            )
            self.compose_up = self.directory.command(
                args=["docker", "compose", "up", "-d"],
            )

        @property
        def compose_content(self):
            content = dict(
                version="3",
                services=dict(
                    app=dict(
                        image="gitea/gitea:1.19.0",
                        volumes=[
                            "./data:/data",
                        ],
                        restart="unless-stopped",
                        ports=[
                            f"{self.props.listen}:3000",
                        ],
                    ),
                ),
            )
            return yaml.dump(content, sort_keys=False)

And replace the content of ``stack.py`` with the following:

.. code-block:: python
    :caption: ``stack.py``

    from pathlib import Path
    from opslib import Component, LocalHost, Stack
    from gitea import Gitea


    class Local(Component):
        def build(self):
            self.host = LocalHost()
            self.gitea = Gitea(
                directory=self.host.directory(Path(__file__).parent / "target"),
                listen="127.0.0.1:3000",
            )


    stack = Stack(__name__)
    stack.local = Local()

We've created two new :class:`~opslib.components.Component` classes to keep the
stack organised.

``Gitea`` represents the application, and we'll be reusing it later, when we
deploy to the cloud. It receives a couple of :ref:`Props`:

* *directory* is the place where it's supposed to deploy itself. Whether it's a
  local or remote directory, the :doc:`places components <../batteries/places>`
  work the same, to create directories, files, and run commands.
* *listen* is the host-side part of the `Compose ports`_ definition.

.. _Compose ports: https://docs.docker.com/compose/compose-file/compose-file-v3/#ports

These props are accessible as ``self.props`` to the component.

The :meth:`~opslib.components.Component.build` method is called when a
*Component* instance is created. It's the natural place to define the structure
of the component by attaching sub-components.

We make sure to attach ``self.props.directory`` as ``self.directory``, so that
it's part of the stack, and gets deployed. Otherwise the directory would not be
created and ``self.compose_file`` would fail.

We've rewritten ``COMPOSE_YML`` as Python, and it gets rendered to YAML on the
fly. This way, we can generate the configuration depending on the *props*.

The ``Local`` component represents the Gitea instance that runs on *localhost*.
In the next step we'll add another instance and it's convenient to wrap each
one in its own *Component*.

If we run ``opslib - diff``, we'll see that the ``docker-compose.yml`` file has
changed, because the indentation of the *YAML* module is slightly different
from our own, and also because the path to the data volume is now an absolute
path. Let's run ``opslib - deploy`` to apply the changes.

Optional port forwarding
------------------------

When we deploy the stack in the cloud, ingress will be configured with
Cloudflare Tunnels, so the Compose service won't need a *port* configuration.
Let's make it optional:

.. code-block:: diff

    --- a/gitea.py
    +++ b/gitea.py
    @@ -1,3 +1,4 @@
    +from typing import Optional
     import yaml
     from opslib import Component, Directory, Prop

    @@ -5,7 +6,7 @@ from opslib import Component, Directory, Prop
     class Gitea(Component):
         class Props:
             directory = Prop(Directory)
    -        listen = Prop(str)
    +        listen = Prop(Optional[str])

         def build(self):
             self.directory = self.props.directory
    @@ -28,10 +29,13 @@ class Gitea(Component):
                             "./data:/data",
                         ],
                         restart="unless-stopped",
    -                    ports=[
    -                        f"{self.props.listen}:3000",
    -                    ],
                     ),
                 ),
             )
    +
    +        if self.props.listen:
    +            content["services"]["app"]["ports"] = [
    +                f"{self.props.listen}:3000",
    +            ]
    +
             return yaml.dump(content, sort_keys=False)

There should be no difference when running ``opslib - diff`` (except for the
``local.gitea.compose_up`` command that is always run).

Running commands only when needed
---------------------------------

Up to now, the ``local.gitea.compose_up`` command is run at each deployment.
The ``docker compose up -d`` command is smart enough to figure out that it
doesn't need to do anything, but it's still unnecessary work, and looks
suspicious in our ``opslib - diff`` output. Let's configure the command to only
run when the contents of ``docker-compose.yml`` changes:

.. code-block:: diff

    --- a/gitea.py
    +++ b/gitea.py
    @@ -16,6 +16,7 @@ class Gitea(Component):
             )
             self.compose_up = self.directory.command(
                 args=["docker", "compose", "up", "-d"],
    +            run_after=[self.compose_file],
             )

         @property

The ``run_after`` prop does exactly what you'd expect: if any of the components
in the list deploys a change, a flag is set in the state of the ``compose_up``
component, so that, when its turn comes to deploy, it will run. You can check
its behaviour by commenting out the ``listen`` prop in ``stack.py`` and running
``opslib - diff`` and ``opslib - deploy``, and then re-running them (which
should not show any ``[changed]`` component).


Extending the CLI
-----------------

The Opslib CLI is built with Click_ and quite flexible – it can be extended
with custom commands for each component. Next we're going to add a ``compose``
command to our *Gitea* component:

.. _Click: https://click.palletsprojects.com/

.. code-block:: diff

    --- a/gitea.py
    +++ b/gitea.py
    @@ -40,3 +40,10 @@ class Gitea(Component):
                 ]

             return yaml.dump(content, sort_keys=False)
    +
    +    def add_commands(self, cli):
    +        @cli.forward_command
    +        def compose(args):
    +            """Run `docker compose` with the given arguments"""
    +            cmd = ["docker", "compose", *args]
    +            self.directory.run(*cmd, capture_output=False, exit=True)

The :meth:`~opslib.components.Component.add_commands` method will be called by
Opslib with an argument that represents the command group for the component.
It's a :class:`click.Group` subclass that adds a handy
:meth:`~opslib.cli.ComponentGroup.forward_command` method that captures all
unhandled arguments and forwards them through the ``args`` argument as an
array. We can then append those arguments to ``docker compose``. And, because
we're running the command using ``self.directory.run`` (which is the
:meth:`~opslib.places.Directory.run` method of
:class:`~opslib.places.Directory`), it will be executed with the compose
directory as its working directory. This pattern is quite useful to run
commands in the context of the component.

We're now going to use this new ``compose`` subcommand to run ``docker compose
down``, tearing down the compose service. Since it's defined on the *Gitea*
component, the first argument to ``opslib`` is the path to the component in the
stack, ``local.app``. The second argument, ``compose``, is the name of the new
command. The remaining arguments (a single one, ``down``) will pe passed on to
``docker compose``.

.. code-block:: none

    $ opslib local.gitea compose down
    [+] Running 2/1
     ✔ Container gitea-app-1  Removed                               1.2s
     ✔ Network gitea_default  Removed                               0.0s


Continue to :doc:`cloud`.
