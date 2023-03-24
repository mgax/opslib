import click

from opslib.components import Component, Stack
from opslib.places import SshHost
from opslib.props import Prop
from opslib.terraform import TerraformProvider


class VPS(Component):
    class Props:
        hetzner = Prop(TerraformProvider)
        name = Prop(str)

    def build(self):
        self.server = self.props.hetzner.resource(
            type="hcloud_server",
            body=dict(
                name=self.props.name,
                server_type="cx11",
                image="debian-11",
                location="hel1",
                ssh_keys=["my-key"],
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


class Example(Stack):
    def build(self):
        self.hetzner = TerraformProvider(
            name="hcloud",
            source="hetznercloud/hcloud",
            version="~> 1.36.2",
        )

        self.vps = VPS(
            hetzner=self.hetzner,
            name="mycodeforge",
        )


def get_stack():
    return Example()
