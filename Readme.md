# Opslib

[![Discord](https://badgen.net/badge/icon/discord?icon=discord&label)](https://discord.gg/TbaFKfusS6)

Opslib is a Python infrastructure-as-code framework which offers powerful abstractions to make deployment straightforward and fun.

### Installing

```shell
$ pip install -U pyopslib
```

## A Simple Example

```python
# stack.py
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
```

Deploy the stack. It's called `-` because it's the top level _Stack_ object:

```shell
export HCLOUD_TOKEN="..."  # https://docs.hetzner.com/cloud/api/getting-started/generating-api-token
opslib - deploy
```

Now we can interact with the VPS host, which we named `vm` above:

```shel
opslib vm run 'set -x; whoami; uptime'
opslib vm run docker run --rm hello-world
```

Finally, we tear down the stack:

```shell
opslib - destroy
```

## Features

Opslib does its best to enable readable code so you can reason about your stack. This means making use of [descriptors](https://docs.python.org/3/howto/descriptor.html), [typing](https://docs.python.org/3/library/typing.html) and other Python language features where it makes sense.

* Defining components
    * Define the stack in terms of [nested components](https://pyopslib.readthedocs.io/en/latest/components.html) with typed [props](https://pyopslib.readthedocs.io/en/latest/components.html#props).
    * [Extensible cli](https://pyopslib.readthedocs.io/en/latest/cli.html): any component in the stack can be referenced directly and may [define its own commands](https://pyopslib.readthedocs.io/en/latest/cli.html#defining-custom-commands).
* Batteries included
    * Terraform: invoke any provider from the Terraform Registry.
    * Ansible: invoke any module from Ansible Collections.
    * Places: native modeling of local/remote hosts, files, directories and shell commands.
    * A handful of specific integrations (e.g. systemd, restic). _I plan to spin them off into a library of reusable components._
* Operations model
    * Most actions boil down to invoking [subprocess commands](https://pyopslib.readthedocs.io/en/latest/api.html#opslib.local.run) or HTTP requests. All actions return [Results](https://pyopslib.readthedocs.io/en/latest/api.html#opslib.results.Result), which are understood by the reporting layer.
    * Many components, after being successfully deployed, are skipped on subsequent deployments, unless their props change, or are manually refreshed to account for remote state changes.
    * [Commands](https://pyopslib.readthedocs.io/en/latest/api.html#opslib.places.Command) may track deployment of other components (e.g. configuration files) and only get re-run when needed.
    * [Lazy variables](https://pyopslib.readthedocs.io/en/latest/components.html#lazy-values), that wrap values which are available after another component is deployed, get evaluated when they are needed.

## Links

* Documentation: https://pyopslib.readthedocs.io
* Examples: https://github.com/mgax/opslib/tree/main/examples
* Discord: https://discord.gg/TbaFKfusS6
