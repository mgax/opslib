# Opslib

Tired of describing your infrastructure with declarative configuration files that make any non-trivial logic awkward? Opslib is a Pythonic toolkit to manage infrastructure, inspired by [AWS CDK](https://aws.amazon.com/cdk/).

Opslib is tiny but it stands on the shoulders of giants. You can use any Terraform Provider, Ansible Module, or directly execute shell commands.

## Example

The code below creates a VPS using the [Hetzner Cloud](https://registry.terraform.io/providers/hetznercloud/hcloud/latest) Terraform provider and installs Docker using the [Ansible `shell` module](https://docs.ansible.com/ansible/latest/collections/ansible/builtin/shell_module.html). It also defines a custom `ssh` command to log into the server.

```python
# stack.py
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
```

To deploy the stack, simply run:

```shell
opslib - deploy
```

Then, check if Docker works, by running the `hello-world` image. `opslib vps ssh` invokes the custom command created in `add_commands`.

```shell
opslib vps ssh docker run --rm hello-world
```

## Documentation

https://pyopslib.readthedocs.io

A good place to start is [the tutorial](https://pyopslib.readthedocs.io/en/latest/tutorial/index.html).
