import os
from pathlib import Path

import click

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
            body=dict(
                name="opslib",
                public_key=Path("~/.ssh/id_rsa.pub").expanduser().read_text(),
            ),
            output=["id"],
        )

        self.server = self.props.hetzner.resource(
            type="hcloud_server",
            body=dict(
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

        self.tailscale = self.props.tailnet.node(
            run=self.host.run,
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


class Example(Stack):
    def build(self):
        self.tailnet = TailscaleNetwork(
            api_key=os.environ["TAILSCALE_API_KEY"],
        )

        self.hetzner = TerraformProvider(
            name="hcloud",
            source="hetznercloud/hcloud",
            version="~> 1.36.2",
        )

        self.vps = VPS(
            hetzner=self.hetzner,
            name="opslib-examples-tailnet",
            tailnet=self.tailnet,
        )


def get_stack():
    return Example()
