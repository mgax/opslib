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


class File(Thing):
    class Props:
        host = Prop(BaseHost)
        path = Prop(Path)
        content = Prop(str)
        mode = Prop(Optional[str])
        owner = Prop(Optional[str])
        group = Prop(Optional[str])

    def build(self):
        args = dict(
            content=self.props.content,
            dest=str(self.props.path),
        )

        if self.props.mode:
            args["mode"] = self.props.mode

        if self.props.owner:
            args["owner"] = self.props.owner

        if self.props.group:
            args["group"] = self.props.group

        self.action = AnsibleAction(
            hostname=self.props.host.hostname,
            ansible_variables=self.props.host.ansible_variables,
            action=dict(
                module="ansible.builtin.copy",
                args=args,
            ),
        )


class Directory(Thing):
    class Props:
        host = Prop(BaseHost)
        path = Prop(Path)
        mode = Prop(Optional[str])
        owner = Prop(Optional[str])
        group = Prop(Optional[str])

    def build(self):
        args = dict(
            path=str(self.props.path),
            state="directory",
        )

        if self.props.mode:
            args["mode"] = self.props.mode

        if self.props.owner:
            args["owner"] = self.props.owner

        if self.props.group:
            args["group"] = self.props.group

        self.action = AnsibleAction(
            hostname=self.props.host.hostname,
            ansible_variables=self.props.host.ansible_variables,
            action=dict(
                module="ansible.builtin.file",
                args=args,
            ),
        )

    def subdir(self, name, **kwargs):
        return Directory(
            host=self.props.host,
            path=self.props.path / name,
            **kwargs,
        )

    def file(self, name, **kwargs):
        return File(
            host=self.props.host,
            path=self.props.path / name,
            **kwargs,
        )


class Command(Thing):
    class Props:
        host = Prop(BaseHost)
        args = Prop(list, default=[])
        input = Prop(Optional[str])

    def deploy(self, dry_run=False):
        if dry_run:
            return Result(changed=True)

        return Lazy(
            self.props.host.run,
            *self.props.args,
            input=self.props.input,
            capture_output=False,
        )
