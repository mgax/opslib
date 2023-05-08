from opslib import SshHost, Stack
from opslib.ansible import AnsibleAction
from opslib.terraform import TerraformProvider

stack = Stack(__name__)

stack.hetzner = TerraformProvider(
    name="hcloud",
    source="hetznercloud/hcloud",
    version="~> 1.38.2",
)

stack.server = stack.hetzner.resource(
    type="hcloud_server",
    args=dict(
        name="opslib-example",
        server_type="cx11",
        image="debian-11",
        location="hel1",
        ssh_keys=["my-key"],
    ),
    output=["ipv4_address"],
)

stack.vm = SshHost(
    hostname=stack.server.output["ipv4_address"],
    username="root",
)

stack.install_docker = AnsibleAction(
    host=stack.vm,
    module="ansible.builtin.shell",
    args=dict(
        cmd="curl -s https://get.docker.com | bash",
        creates="/opt/bin/docker",
    ),
)
