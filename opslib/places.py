import os
import sys
from pathlib import Path
from typing import Optional

from .ansible import AnsibleAction
from .lazy import Lazy
from .local import run
from .props import Prop
from .results import Result
from .things import Thing


class BaseHost:
    def file(self, **kwargs):
        return File(
            host=self,
            **kwargs,
        )

    def directory(self, **kwargs):
        return Directory(
            host=self,
            **kwargs,
        )

    def command(self, **kwargs):
        return Command(
            host=self,
            **kwargs,
        )

    def ansible_action(self, **kwargs):
        return AnsibleAction(
            hostname=self.hostname,
            ansible_variables=self.ansible_variables,
            **kwargs,
        )


class LocalHost(BaseHost):
    hostname = "localhost"
    ansible_variables = [
        ("ansible_connection", "local"),
        ("ansible_python_interpreter", sys.executable),
    ]

    def run(self, *args, **kwargs):
        if not args:
            shell = os.environ.get("SHELL", "sh")
            args = [shell]
        return run(*args, **kwargs)


class SshHost(BaseHost):
    def __init__(
        self,
        hostname,
        username=None,
        port=None,
        private_key_file=None,
        config_file=None,
        interpreter="python3",
    ):
        self.hostname = hostname
        self.port = port
        self.username = username
        self.private_key_file = private_key_file
        self.config_file = config_file
        self.ansible_variables = [
            ("ansible_python_interpreter", interpreter),
        ]

        if port:
            self.ansible_variables.append(("ansible_ssh_port", str(port)))

        if username:
            self.ansible_variables.append(("ansible_user", username))

        if private_key_file:
            self.ansible_variables.append(
                ("ansible_ssh_private_key_file", str(private_key_file))
            )

        if config_file:
            self.ansible_variables.append(
                ("ansible_ssh_common_args", f"-F {config_file}"),
            )

    def run(self, *args, **kwargs):
        hostname = self.hostname
        if self.username:
            hostname = f"{self.username}@{hostname}"

        ssh_args = ["ssh", hostname]
        if self.port:
            ssh_args += ["-p", str(self.port)]

        if self.private_key_file:
            ssh_args += ["-i", str(self.private_key_file)]

        if self.config_file:
            ssh_args += ["-F", str(self.config_file)]

        return run(*ssh_args, "--", *args, **kwargs)


class File(Thing):
    class Props:
        host = Prop(BaseHost)
        path = Prop(Path)
        content = Prop(str)
        mode = Prop(Optional[str])
        owner = Prop(Optional[str])
        group = Prop(Optional[str])

    @property
    def host(self):
        return self.props.host

    @property
    def path(self):
        return self.props.path

    def build(self):
        args = dict(
            content=self.props.content,
            dest=str(self.path),
        )

        if self.props.mode:
            args["mode"] = self.props.mode

        if self.props.owner:
            args["owner"] = self.props.owner

        if self.props.group:
            args["group"] = self.props.group

        self.action = self.host.ansible_action(
            module="ansible.builtin.copy",
            args=args,
        )


class Directory(Thing):
    class Props:
        host = Prop(BaseHost)
        path = Prop(Path)
        mode = Prop(Optional[str])
        owner = Prop(Optional[str])
        group = Prop(Optional[str])

    @property
    def host(self):
        return self.props.host

    @property
    def path(self):
        return self.props.path

    def build(self):
        args = dict(
            path=str(self.path),
            state="directory",
        )

        if self.props.mode:
            args["mode"] = self.props.mode

        if self.props.owner:
            args["owner"] = self.props.owner

        if self.props.group:
            args["group"] = self.props.group

        self.action = self.host.ansible_action(
            module="ansible.builtin.file",
            args=args,
        )

    def subdir(self, name, **kwargs):
        return Directory(
            host=self.host,
            path=self.path / name,
            **kwargs,
        )

    def __truediv__(self, name):
        return self.subdir(name)

    def file(self, name, **kwargs):
        return File(
            host=self.host,
            path=self.path / name,
            **kwargs,
        )


class Command(Thing):
    class Props:
        host = Prop(BaseHost)
        args = Prop(list, default=[])
        input = Prop(Optional[str])

    @property
    def host(self):
        return self.props.host

    def deploy(self, dry_run=False):
        if dry_run:
            return Result(changed=True)

        return Lazy(
            self.host.run,
            *self.props.args,
            input=self.props.input,
            capture_output=False,
        )
