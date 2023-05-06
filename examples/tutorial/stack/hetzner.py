from pathlib import Path

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
            body=dict(
                name="opslib-tutorial",
                public_key=Path("~/.ssh/id_rsa.pub").expanduser().read_text(),
            ),
            output=["id"],
        )

        self.host = SshHost(
            hostname=self.server.output["ipv4_address"],
            username="root",
        )

        self.server = self.provider.resource(
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

        self.install_docker = self.host.ansible_action(
            module="ansible.builtin.shell",
            args=dict(
                cmd="curl -s https://get.docker.com | bash",
                creates="/opt/bin/docker",
            ),
        )
