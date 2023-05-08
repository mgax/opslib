from opslib.components import Component
from opslib.lazy import evaluate, lazy_property
from opslib.places import SshHost
from opslib.props import Prop
from opslib.terraform import TerraformProvider


class VPS(Component):
    class Props:
        hostname = Prop(str)

    def build(self):
        # https://registry.terraform.io/providers/hetznercloud/hcloud/latest/docs
        self.provider = TerraformProvider(
            name="hcloud",
            source="hetznercloud/hcloud",
            version="~> 1.38.2",
        )

        self.ssh_keys = self.provider.data(
            type="hcloud_ssh_keys",
            output=["ssh_keys"],
        )

        self.images = self.provider.data(
            type="hcloud_images",
            args=dict(
                with_architecture=["x86"],
            ),
            output=["images"],
        )

        self.server = self.provider.resource(
            type="hcloud_server",
            args=dict(
                name=self.props.hostname,
                server_type="cx11",
                image=self.image_id,
                location="hel1",
                ssh_keys=self.ssh_key_names,
            ),
            output=["id", "ipv4_address"],
        )

        self.reverse_dns = self.provider.resource(
            type="hcloud_rdns",
            args=dict(
                server_id=self.server.output["id"],
                ip_address=self.server.output["ipv4_address"],
                dns_ptr=self.props.hostname,
            ),
        )

        self.host = SshHost(
            hostname=self.server.output["ipv4_address"],
            username="root",
        )

        # https://docs.ansible.com/ansible/latest/collections/ansible/builtin/shell_module.html
        self.install_docker = self.host.ansible_action(
            module="ansible.builtin.shell",
            args=dict(
                cmd="curl -s https://get.docker.com | bash",
                creates="/usr/bin/docker",
            ),
        )

    @lazy_property
    def ssh_key_names(self):
        return [key["name"] for key in evaluate(self.ssh_keys.output["ssh_keys"])]

    @lazy_property
    def image_id(self):
        images = evaluate(self.images.output["images"])
        [image] = [i for i in images if i["name"] == "debian-11"]
        return image["id"]
