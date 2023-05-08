Deploying to a VPS
==================

We're going to create a VPS at Hetzner, using the official `Hetzner Cloud Provider`_. First create an account and `get an API token`_.

.. _Hetzner Cloud Provider: https://registry.terraform.io/providers/hetznercloud/hcloud/latest/docs
.. _get an API token: https://docs.hetzner.cloud/#getting-started

Copy the token to ``.envrc``:

.. code-block:: none
    :caption: ``.envrc``

    source .venv/bin/activate
    export HCLOUD_TOKEN=...

Run ``direnv allow`` to approve it.

Now let's define our VPS in a new file, ``stack/hetzner.py``. We configure the Terraform provider, SSH identity key, the VPS itself, and install Docker.

.. code-block:: python
    :caption: ``stack/hetzner.py``

    from pathlib import Path
    import click
    from opslib.components import Component
    from opslib.places import SshHost
    from opslib.props import Prop
    from opslib.terraform import TerraformProvider

    class VPS(Component):
        class Props:
            name = Prop(str)

        def build(self):
            self.provider = TerraformProvider(
                name="hcloud",
                source="hetznercloud/hcloud",
                version="~> 1.36.2",
            )

            self.ssh_key = self.provider.resource(
                type="hcloud_ssh_key",
                args=dict(
                    name="opslib-tutorial",
                    public_key=Path("~/.ssh/id_rsa.pub").expanduser().read_text(),
                ),
                output=["id"],
            )

            self.server = self.provider.resource(
                type="hcloud_server",
                args=dict(
                    name=self.props.name,
                    server_type="cx11",
                    image="debian-11",
                    location="hel1",
                    ssh_keys=[
                        self.ssh_key.output["id"],
                    ],
                ),
                output=["ipv4_address"],
            )

            self.install_docker = self.host.ansible_action(
                module="ansible.builtin.shell",
                args=dict(
                    cmd="curl -s https://get.docker.com | bash",
                    creates="/opt/bin/docker",
                ),
            )

        @property
        def host(self):
            return SshHost(
                hostname=self.server.output["ipv4_address"],
                username="root",
            )

        def add_commands(self, cli):
            @cli.command(context_settings=dict(ignore_unknown_options=True))
            @click.argument("args", nargs=-1, type=click.UNPROCESSED)
            def ssh(args):
                self.host.run(*args, capture_output=False, exit=True)

Now we need to attach the VPS to our stack and change the Gitea configuration
to deploy to the VPS. Here is the new ``stack/__init__.py``:

.. code-block:: python
    :caption: ``stack/__init__.py``

    import os
    from opslib.components import Stack
    from .gitea import Gitea
    from .hetzner import VPS

    class MyCodeForge(Stack):
        def build(self):
            self.vps = VPS(
                name="mycodeforge",
            )

            self.directory = self.vps.host.directory("/opt/opslib")

            self.gitea = Gitea(
                directory=self.directory / "gitea",
                listen="3000",
            )

    def get_stack():
        return MyCodeForge()

Let's run ``diff`` to see what will get deployed.

.. code-block:: none

    opslib - diff
    vps.ssh_key TerraformResource [changed]
      # hcloud_ssh_key.thing will be created
      + resource "hcloud_ssh_key" "thing" {
          + fingerprint = (known after apply)
          + id          = (known after apply)
          + name        = "opslib-tutorial"
          + public_key  = <<-EOT
                ssh-rsa [...]
            EOT
        }

    Plan: 1 to add, 0 to change, 0 to destroy.

    Changes to Outputs:
      + id = (sensitive value)
    vps.server TerraformResource ...
    vps.server TerraformResource [failed]
    <TerraformResource vps.ssh_key>: output 'id' not available
    gitea.directory.action AnsibleAction [ok]
    gitea.data_volume.action AnsibleAction [ok]
    gitea.compose_file.action AnsibleAction [ok]
    gitea.compose_up Command [changed]
    3 ok
    2 changed
    1 failed
    <class 'opslib.terraform.TerraformResource'>: 2
    <class 'opslib.places.Command'>: 1

Terraform tells us that it will deploy the SSH key, but the server resource
fails. This is because the server definition depends on
``self.ssh_key.output["id"]``, the Hetzner ID for the key resource, which is
not yet available, since the key is not yet deployed. So let's deploy the key.


.. code-block:: none

    opslib vps.ssh_key deploy
    opslib - diff

Now there should be no errors. We could have deployed the whole stack in one
go, instead of deploying ``vps.ssh_key`` separately, because the ``args``
prop of the server resource is only evaluated when it's time to deploy it.

Let's go ahead and deploy the whole stack:

.. code-block:: none

    opslib - deploy

Some things that might go wrong:

* The first time opslib tries to run any command in the new server, you will be
  prompted to verify its SSH serveer key. Type "yes" and presss enter.
* Docker version ``23.0.1`` needs *apparmor*, which is not installed by default
  on Debian. Install it and restart Docker::

    opslib vps ssh apt install apparmor
    opslib vps ssh systemctl restart docker

  You can always check if Docker works by running the ``hello-world`` image::

    opslib vps ssh docker run --rm hello-world

  Then try ``opslib - deploy`` again.

When the deployment is successful, get the IP address of the VPS:

.. code-block:: none

    opslib vps.server terraform output -json

Then open Gitea in the browser at ``http://{ipv4_address}:3000/``.

Configuring https is left as an exercise to the reader
(https://docs.gitea.io/en-us/https-setup/).

Tear-down
^^^^^^^^^

The VPS is billed hourly so we should delete it when we're done:

.. code-block:: none

    $ opslib vps.server terraform destroy
