import os
from pathlib import Path

from opslib.components import Component, Stack
from opslib.extras.tailscale import TailscaleNetwork
from opslib.places import SshHost
from opslib.props import Prop
from opslib.terraform import TerraformProvider


class VPS(Component):
    class Props:
        hetzner = Prop(TerraformProvider)
        name = Prop(str)
        tailnet = Prop(TailscaleNetwork)

    def build(self):
        self.ssh_key = self.props.hetzner.resource(
            type="hcloud_ssh_key",
            args=dict(
                name="opslib",
                public_key=Path("~/.ssh/id_rsa.pub").expanduser().read_text(),
            ),
            output=["id"],
        )

        self.server = self.props.hetzner.resource(
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

        self.tailscale = self.props.tailnet.node(
            run=self.host.run,
        )


stack = Stack(__name__)

stack.tailnet = TailscaleNetwork(
    api_key=os.environ["TAILSCALE_API_KEY"],
)

stack.hetzner = TerraformProvider(
    name="hcloud",
    source="hetznercloud/hcloud",
    version="~> 1.36.2",
)

stack.vps = VPS(
    hetzner=stack.hetzner,
    name="opslib-examples-tailnet",
    tailnet=stack.tailnet,
)
