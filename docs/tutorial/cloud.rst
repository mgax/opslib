Deploying to The Cloud
======================

The goal here is to deploy our application from the last step, :doc:`local`, in
the cloud. We'll use the :doc:`Terraform wrapper <../batteries/terraform>` to
create a `Hetzner VPS`_ and a `Cloudflare Tunnel`_ for ingress. The Cloudflare
Tunnel handles HTTPS for us automatically, and it doesn't require our server to
accept any inbound traffic directly.

.. _Hetzner VPS: https://registry.terraform.io/providers/hetznercloud/hcloud/latest/docs/resources/server
.. _Cloudflare Tunnel: https://registry.terraform.io/providers/cloudflare/cloudflare/latest/docs/resources/tunnel

Hetzner VPS
-----------

First you'll need to create a Hetzner account and `get an API token`_. Copy the
token to ``.envrc`` and run ``direnv allow`` to approve it.

.. _get an API token: https://docs.hetzner.cloud/#getting-started

.. code-block:: none
    :caption: ``.envrc``

    # [...]
    export HCLOUD_TOKEN=[...]

Now let's define our VPS in a new file, ``hetzner.py``. We configure the
Terraform provider, SSH identity key, the VPS itself, and install Docker.

.. code-block:: python
    :caption: ``hetzner.py``

    from pathlib import Path
    from opslib import Component, Prop, SshHost
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

            self.host = SshHost(
                hostname=self.server.output["ipv4_address"],
                username="root",
            )

            self.install_docker = self.host.ansible_action(
                module="ansible.builtin.shell",
                args=dict(
                    cmd="curl -s https://get.docker.com | bash",
                    creates="/opt/bin/docker",
                ),
            )

Now we need to attach the VPS to our stack and change the Gitea configuration
to deploy to the VPS. Add the following to ``stack.py``:

.. code-block:: diff

    --- a/stack.py
    +++ b/stack.py
    @@ -1,6 +1,7 @@
     from pathlib import Path
     from opslib import Component, LocalHost, Stack
     from gitea import Gitea
    +from hetzner import VPS


     class Local(Component):
    @@ -12,5 +13,16 @@ class Local(Component):
             )


    +class Cloud(Component):
    +    def build(self):
    +        self.vps = VPS(
    +            name="opslib-tutorial",
    +        )
    +        self.gitea = Gitea(
    +            directory=self.vps.host.directory("/opt/gitea"),
    +        )
    +
    +
     stack = Stack(__name__)
     stack.local = Local()
    +stack.cloud = Cloud()

Because the *directory* prop of ``stack.cloud.gitea`` is a directory created
from the VPS host, it will deploy its files and run its commands on that host.
Quite convenient.

Let's run ``diff`` to see what will get deployed.

.. code-block:: none

    opslib - diff
    cloud.vps.ssh_key TerraformResource [changed]
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
    cloud.vps.server TerraformResource ...
    cloud.vps.server TerraformResource [failed]
    <TerraformResource cloud.vps.ssh_key>: output 'id' not available
    cloud.gitea.directory.action AnsibleAction [ok]
    cloud.gitea.data_volume.action AnsibleAction [ok]
    cloud.gitea.compose_file.action AnsibleAction [ok]
    cloud.gitea.compose_up Command [changed]
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

    opslib cloud.vps.ssh_key deploy
    opslib - diff

Now there should be no errors. We could have deployed the whole stack in one
go, instead of deploying ``cloud.vps.ssh_key`` separately, because the ``args``
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

  Then try ``opslib - deploy`` again.

Cloudflare Tunnel
-----------------

This step assumes you have a Cloudflare account with a "Website" (DNS zone)
already set up. You'll need to `create an API token`_ with the following permissions:

.. _create an API token: https://developers.cloudflare.com/fundamentals/api/get-started/create-token/

* "Account" > "Cloudflare Tunnel" > "Edit"
* "Zone" > "DNS" > "Edit"

We're also going to set these additional environment variables:

* *CLOUDFLARE_ZONE_NAME*: name of the Cloudflare DNS zone, e.g. ``example.com``.
* *CLOUDFLARE_RECORD_NAME*: record name for the website, e.g. ``gitea``,
  resulting in the FQDN ``gitea.example.com``.
* *CLOUDFLARE_TUNNEL_SECRET*: random secret for the tunnel. You can generate
  one with this command: ``python3 -c "import secrets;
  print(secrets.token_urlsafe())"``.

Copy the environment variables to ``.envrc`` and run ``direnv allow`` to
approve it.

.. code-block:: none
    :caption: ``.envrc``

    # [...]
    export CLOUDFLARE_API_TOKEN=[...]
    export CLOUDFLARE_ZONE_NAME=[...]
    export CLOUDFLARE_RECORD_NAME=[...]
    export CLOUDFLARE_TUNNEL_SECRET=[...]

Copy the following to ``cloudflare.py``:

.. code-block:: python
    :caption: ``cloudflare.py``

    from base64 import b64encode
    from functools import cached_property
    from opslib import Component, Prop, evaluate, lazy_property
    from opslib.terraform import TerraformProvider


    class Cloudflare(Component):
        class Props:
            zone_name = Prop(str)
            record_name = Prop(str)
            tunnel_secret = Prop(str)

        def build(self):
            self.provider = TerraformProvider(
                name="cloudflare",
                source="cloudflare/cloudflare",
                version="~> 4.2",
            )

            self.zone = self.provider.data(
                type="cloudflare_zone",
                args=dict(
                    name=self.props.zone_name,
                ),
                output=["id", "account_id"],
            )

            self.tunnel = self.provider.resource(
                type="cloudflare_tunnel",
                args=dict(
                    account_id=self.zone.output["account_id"],
                    name=self.props.record_name,
                    secret=self.secret_base64,
                ),
                output=["id"],
            )

            self.cname = self.provider.resource(
                type="cloudflare_record",
                args=dict(
                    zone_id=self.zone.output["id"],
                    name=self.props.record_name,
                    type="CNAME",
                    value=self.tunnel_cname,
                    proxied=True,
                ),
            )

        @cached_property
        def secret_base64(self):
            return b64encode(self.props.tunnel_secret.encode()).decode()

        @lazy_property
        def tunnel_cname(self):
            return f"{evaluate(self.tunnel.output['id'])}.cfargotunnel.com"

We're using resources from the `Terraform Cloudflare Provider`_. First we set
up a :ref:`data source <Data Sources>` of type cloudflare_zone_ to fetch the
*zone id* of the DNS zone, and the *account id* of the account. Then we create
:ref:`resources <Resources>` – a cloudflare_tunnel_ to connect our Gitea
application, and a cloudflare_record_ to receive traffic for the tunnel.

.. _Terraform Cloudflare Provider: https://registry.terraform.io/providers/cloudflare/cloudflare/4.6.0/docs
.. _cloudflare_zone: https://registry.terraform.io/providers/cloudflare/cloudflare/4.6.0/docs/data-sources/zone
.. _cloudflare_tunnel: https://registry.terraform.io/providers/cloudflare/cloudflare/4.6.0/docs/resources/tunnel
.. _cloudflare_record: https://registry.terraform.io/providers/cloudflare/cloudflare/4.6.0/docs/resources/record

Next we need to instantiate the *Cloudflare* component we've just defined. Add
the following to ``stack.py``:

.. code-block:: diff

    --- a/stack.py
    +++ b/stack.py
    @@ -1,5 +1,7 @@
    +import os
     from pathlib import Path
     from opslib import Component, LocalHost, Stack
    +from cloudflare import Cloudflare
     from gitea import Gitea
     from hetzner import VPS

    @@ -18,6 +20,11 @@ class Cloud(Component):
             self.vps = VPS(
                 name="opslib-tutorial",
             )
    +        self.cloudflare = Cloudflare(
    +            zone_name=os.environ["CLOUDFLARE_ZONE_NAME"],
    +            record_name=os.environ.get("CLOUDFLARE_RECORD_NAME", "example-gitea"),
    +            tunnel_secret=os.environ["CLOUDFLARE_TUNNEL_SECRET"],
    +        )
             self.gitea = Gitea(
                 directory=self.vps.host.directory("/opt/gitea"),
             )

Now run ``opslib - deploy`` to create the tunnel and CNAME record.

Connecting Gitea to the tunnel
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The final step is to run cloudflared_ as a sidecar next to Gitea so that it can
proxy traffic from Cloudflare to our app. Our *Cloudflare* component will
implement a method that, given the URL of the upstream service (Gitea itself),
defines a Compose service that runs *cloudflared*, with the right arguments.
Add the following to ``cloudflare.py``:

.. _cloudflared: https://github.com/cloudflare/cloudflared

.. code-block:: diff

    --- a/cloudflare.py
    +++ b/cloudflare.py
    @@ -1,3 +1,4 @@
    +import json
     from base64 import b64encode
     from functools import cached_property
     from opslib import Component, Prop, evaluate, lazy_property
    @@ -53,3 +54,18 @@ class Cloudflare(Component):
         @lazy_property
         def tunnel_cname(self):
             return f"{evaluate(self.tunnel.output['id'])}.cfargotunnel.com"
    +
    +    def token(self):
    +        payload = {
    +            "a": evaluate(self.zone.output["account_id"]),
    +            "t": evaluate(self.tunnel.output["id"]),
    +            "s": evaluate(self.secret_base64),
    +        }
    +        return b64encode(json.dumps(payload).encode("utf8")).decode("utf8")
    +
    +    def sidecar(self, url):
    +        return dict(
    +            image="cloudflare/cloudflared",
    +            command=f"tunnel --no-autoupdate run --token {self.token()} --url {url}",
    +            restart="unless-stopped",
    +        )

Pass on the ``sidecar`` bound method to the *Gitea* component:

.. code-block:: diff

    --- a/stack.py
    +++ b/stack.py
    @@ -27,6 +27,7 @@ class Cloud(Component):
             )
             self.gitea = Gitea(
                 directory=self.vps.host.directory("/opt/gitea"),
    +            sidecar=self.cloudflare.sidecar,
             )

Finally, add the *sidecar* service to the Compose file:

.. code-block:: diff

    --- a/gitea.py
    +++ b/gitea.py
    @@ -1,12 +1,14 @@
    +from collections.abc import Callable
     from typing import Optional
     import yaml
    -from opslib import Component, Directory, Prop
    +from opslib import Component, Directory, Prop, lazy_property


     class Gitea(Component):
         class Props:
             directory = Prop(Directory)
             listen = Prop(Optional[str])
    +        sidecar = Prop(Optional[Callable])

         def build(self):
             self.directory = self.props.directory
    @@ -19,7 +21,7 @@ class Gitea(Component):
                 run_after=[self.compose_file],
             )

    -    @property
    +    @lazy_property
         def compose_content(self):
             content = dict(
                 version="3",
    @@ -39,6 +41,9 @@ class Gitea(Component):
                     f"{self.props.listen}:3000",
                 ]

    +        if self.props.sidecar:
    +            content["services"]["sidecar"] = self.props.sidecar("http://app:3000")
    +
             return yaml.dump(content, sort_keys=False)

         def add_commands(self, cli):

This example nicely illustrares the loose coupling of components: *Gitea* only
knows it's getting a sidecar that points to port 3000 of the *app* container;
it's up to the *Cloudflare* component to provide the tunnel token.

We are switching the ``compose_content`` property to a
:func:`~opslib.lazy.lazy_property` because it needs to be evaluated during
deployment, not when the stack is defined, because the sidecar needs output
from Terraform components (the zone and the tunnel), that is only available
after they are deployed.

Again, let's deploy: ``opslib - deploy``. If all goes well, Gitea will be
available through Cloudflare, at
``https://{CLOUDFLARE_RECORD_NAME}.{CLOUDFLARE_ZONE_NAME}``. Great success!

Tear down the VPS
-----------------

The VPS is billed hourly so we should delete it when we're done:

.. code-block:: none

    $ opslib cloud.vps.server destroy
