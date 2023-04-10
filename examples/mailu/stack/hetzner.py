from pathlib import Path

import click

from opslib.components import Component
from opslib.places import SshHost
from opslib.props import Prop
from opslib.terraform import TerraformProvider


class VPS(Component):
    class Props:
        hostname = Prop(str)

    def build(self):
        self.provider = TerraformProvider(
            name="hcloud",
            source="hetznercloud/hcloud",
            version="~> 1.36.2",
        )

        self.ssh_key = self.provider.resource(
            type="hcloud_ssh_key",
            body=dict(
                name="opslib-example-mailu",
                public_key=Path("~/.ssh/id_rsa.pub").expanduser().read_text(),
            ),
            output=["id"],
        )

        self.server = self.provider.resource(
            type="hcloud_server",
            body=dict(
                name=self.props.hostname,
                server_type="cx11",
                image="debian-11",
                location="hel1",
                ssh_keys=[self.ssh_key.output["id"]],
            ),
            output=["id", "ipv4_address"],
        )

        self.reverse_dns = self.provider.resource(
            type="hcloud_rdns",
            body=dict(
                server_id=self.server.output["id"],
                ip_address=self.server.output["ipv4_address"],
                dns_ptr=self.props.hostname,
            ),
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
