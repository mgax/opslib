import sys
from pathlib import Path

from .ansible import AnsibleAction
from .props import Prop
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


class LocalHost(BaseHost):
    hostname = "localhost"
    ansible_variables = [
        ("ansible_connection", "local"),
        ("ansible_python_interpreter", sys.executable),
    ]


class File(Thing):
    class Props:
        host = Prop(BaseHost)
        path = Prop(Path)
        content = Prop(str)

    def build(self):
        self.action = AnsibleAction(
            hostname=self.props.host.hostname,
            ansible_variables=self.props.host.ansible_variables,
            action=dict(
                module="ansible.builtin.copy",
                args=dict(
                    content=self.props.content,
                    dest=str(self.props.path),
                ),
            ),
        )


class Directory(Thing):
    class Props:
        host = Prop(BaseHost)
        path = Prop(Path)

    def build(self):
        self.action = AnsibleAction(
            hostname=self.props.host.hostname,
            ansible_variables=self.props.host.ansible_variables,
            action=dict(
                module="ansible.builtin.file",
                args=dict(
                    path=str(self.props.path),
                    state="directory",
                ),
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
