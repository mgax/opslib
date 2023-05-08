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
            args=dict(
                name=self.props.name,
                server_type="cx11",
                image="debian-11",
                location="hel1",
                ssh_keys=["my-key"],
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


stack = Stack(__name__)

stack.hetzner = TerraformProvider(
    name="hcloud",
    source="hetznercloud/hcloud",
    version="~> 1.36.2",
)

stack.vps = VPS(
    hetzner=stack.hetzner,
    name="mycodeforge",
)
