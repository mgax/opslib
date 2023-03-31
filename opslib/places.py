import os
import sys
from copy import copy
from pathlib import Path
from typing import Optional, Union

from .ansible import AnsibleAction
from .callbacks import Callbacks
from .components import Component
from .lazy import Lazy, evaluate
from .local import run
from .props import Prop
from .results import Result
from .state import JsonState
from .utils import diff


class BaseHost:
    """
    Abstract class for a host.
    """

    with_sudo = False

    def file(self, **props):
        """
        Shorthand function that returns a :class:`File` component with ``host``
        set to this host. Keyword arguments are forwarded as props to the File.
        """

        return File(
            host=self,
            **props,
        )

    def directory(self, path, **props):
        """
        Shorthand function that returns a :class:`Directory` component with
        ``host`` set to this host. Keyword arguments are forwarded as props to
        the Directory.
        """

        return Directory(
            host=self,
            path=Path(path),
            **props,
        )

    def command(self, **props):
        """
        Shorthand function that returns a :class:`Command` component with
        ``host`` set to this host. Keyword arguments are forwarded as props to
        the Command.
        """

        return Command(
            host=self,
            **props,
        )

    def ansible_action(self, **props):
        """
        Shorthand function that returns an
        :class:`~opslib.ansible.AnsibleAction` component with ``hostname`` and
        ``ansible_variables`` set from this host. Keyword arguments are
        forwarded as props to *AnsibleAction*.
        """

        return AnsibleAction(
            hostname=self.hostname,
            ansible_variables=self.ansible_variables,
            **props,
        )

    def sudo(self):
        """
        Returns a copy of this host that has the ``with_sudo`` flag set. This
        means that commands will be run using ``sudo``, and Ansible will be
        invoked with ``become=True``.
        """

        rv = copy(self)
        rv.with_sudo = True
        rv.ansible_variables = [
            *rv.ansible_variables,
            ("ansible_become", "yes"),
            ("ansible_become_method", "sudo"),
            ("ansible_become_user", "root"),
        ]
        return rv


class LocalHost(BaseHost):
    """
    The local host on which opslib is running. It receives no arguments.

    :ivar hostname: Set to ``localhost``.
    :ivar ansible_variables: Two variables are set: ``ansible_connection`` is
                             ``local``; ``ansible_python_interpreter`` is set
                             to :obj:`sys.executable`.
    """

    hostname = "localhost"
    ansible_variables = [
        ("ansible_connection", "local"),
        ("ansible_python_interpreter", sys.executable),
    ]

    def run(self, *args, **kwargs):
        """
        Run a command on the local host. If ``args`` is empty, it defaults to a
        single argument, ``$SHELL``.

        It invokes :func:`~opslib.local.run` with the arguments.
        """

        if not args:
            shell = os.environ.get("SHELL", "sh")
            args = [shell]
        return run(*args, **kwargs)


class SshHost(BaseHost):
    """
    Connect to a remote host over SSH. Most arguments configure how the ``ssh``
    subcommand is invoked. If you have already configured the host in
    ``~/.ssh/config``, it's enough to specify ``hostname``, as you would in the
    terminal.

    :param hostname: Name of the remote host.
    :param username: Username to log in.
    :param port: Port number.
    :param private_key_file: Path to an SSH identity file to be used for
                             authentication.
    :param config_file: SSH configuration file to use instead of
                        ``~/.ssh/config``.
    :param interpreter: Python interpreter to be used by Ansible. Set as the
                        ``ansible_python_interpreter`` variable. Defaults to
                        ``"python3"``.
    """

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
        """
        Run a command on the remote host.

        It uses :func:`~opslib.local.run` to invoke ``ssh`` with the given
        arguments.
        """

        hostname = evaluate(self.hostname)
        if self.username:
            hostname = f"{self.username}@{hostname}"

        ssh_args = ["ssh", hostname]
        if self.port:
            ssh_args += ["-p", str(self.port)]

        if self.private_key_file:
            ssh_args += ["-i", str(self.private_key_file)]

        if self.config_file:
            ssh_args += ["-F", str(self.config_file)]

        ssh_args.append("--")

        if self.with_sudo:
            ssh_args.append("sudo")
            if not args:
                args = ["-i"]

        return run(*ssh_args, *args, **kwargs)


class File(Component):
    """
    The File component creates a regular file on the host.

    :param host: The parent host.
    :param path: Absolute path of the file.
    :param content: Content to write to the file. May be :class:`str` or
                    :class:`bytes`. May be :class:`~opslib.lazy.Lazy`.
    :param mode: Unix file permissions (optional).
    :param owner: The name of the user owning the directory (optional).
    :param group: The name of the group owning the directory (optional).
    """

    class Props:
        host = Prop(BaseHost)
        path = Prop(Path)
        content = Prop(str, lazy=True)
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
            format_output=self.format_output,
        )

    def format_output(self, result):
        if result.changed:
            return "".join(
                diff(self.path, d["before"], d["after"]) for d in result.data["diff"]
            )

        return ""

    @property
    def on_change(self):
        return self.action.on_change


class Directory(Component):
    """
    The Directory component creates a directory on the host.

    :param host: The parent host.
    :param path: Absolute path of the directory.
    :param mode: Unix file permissions (optional).
    :param owner: The name of the user owning the directory (optional).
    :param group: The name of the group owning the directory (optional).
    """

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
        """
        Shorthand function that returns a :class:`Directory` with the same
        host, and the path being a child path of ``self.path``.
        """

        return Directory(
            host=self.host,
            path=self.path / name,
            **kwargs,
        )

    def __truediv__(self, name):
        """
        Same as :meth:`subdir`.
        """

        return self.subdir(name)

    def file(self, name, **kwargs):
        """
        Shorthand function that returns a :class:`File` with the same
        host, and the path being a child path of ``self.path``.
        """

        return File(
            host=self.host,
            path=self.path / name,
            **kwargs,
        )


class Command(Component):
    """
    The Command component represents a command that should be run on the
    host during deployment.

    :param host: The parent host.
    :param args: Command arguments array. The first argument is the command
                 itself. Defaults to ``[]``, which invokes the shell, useful
                 with the ``input`` parameter.
    :param input: Content to be sent to standard input. Defaults to no input.
    :param run_after: A list of components that trigger this command to be run.
                      If empty, the command will always be run, otherwise it
                      will run once, and then only run after one of the
                      components changes.
    """

    class Props:
        host = Prop(BaseHost)
        args = Prop(Union[list, tuple], default=[])
        input = Prop(Optional[str])
        run_after = Prop(list, default=[])

    state = JsonState()
    on_change = Callbacks()

    @property
    def host(self):
        return self.props.host

    def _set_must_run(self):
        self.state["must-run"] = True

    def run(self, **kwargs):
        """
        Run the command defined by this component.

        :param kwargs: Extra keyword arguments to be forwarded to the ``run``
                       method of the host.
        """

        return self.host.run(
            *self.props.args,
            input=self.props.input,
            **kwargs,
        )

    def build(self):
        for other in self.props.run_after:
            other.on_change.add(self._set_must_run)

    def deploy(self, dry_run=False):
        if self.props.run_after and not self.state.get("must-run"):
            return Result()

        if dry_run:
            return Result(changed=True)

        def _run():
            self.on_change.invoke()
            result = self.run(capture_output=False)
            self.state["must-run"] = False
            return result

        return Lazy(_run)

    def add_commands(self, cli):
        @cli.command
        def run():
            self.run(capture_output=False, exit=True)
