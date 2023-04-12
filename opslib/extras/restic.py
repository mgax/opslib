from io import StringIO
from shlex import quote

import click

from opslib.components import Component
from opslib.lazy import Lazy, evaluate, lazy_property
from opslib.local import run
from opslib.props import Prop
from opslib.results import OperationError, Result
from opslib.state import JsonState

BASH_PREAMBLE = """\
#!/bin/bash
set -euo pipefail
"""


class ResticRepository(Component):
    class Props:
        repository = Prop(str)
        password = Prop(str, lazy=True)
        env = Prop(dict, default={}, lazy=True)

    state = JsonState()

    def refresh(self):
        try:
            self.run("list", "index")
            self.state["initialized"] = True

        except OperationError as error:
            marker = "Is there a repository at the following location?"
            if marker not in error.result.output:
                raise

            self.state["initialized"] = False

        return Result(changed=not self.state["initialized"])

    def deploy(self, dry_run=False):
        if self.initialized:
            return Result()

        if dry_run:
            return Result(changed=True)

        def _run():
            result = self.run("init", "--repository-version=1", capture_output=False)
            self.state["initialized"] = True
            return result

        return Lazy(_run)

    @property
    def extra_env(self):
        return dict(
            RESTIC_REPOSITORY=self.props.repository,
            RESTIC_PASSWORD=evaluate(self.props.password),
            **evaluate(self.props.env),
        )

    def run(self, *args, **kwargs):
        return run("restic", *args, **kwargs, extra_env=self.extra_env)

    @property
    def initialized(self):
        return self.state.get("initialized")

    def plan(self, **props):
        return ResticPlan(repository=self, **props)

    def add_commands(self, cli):
        @cli.command(
            context_settings=dict(
                ignore_unknown_options=True,
                allow_interspersed_args=False,
            )
        )
        @click.argument("args", nargs=-1, type=click.UNPROCESSED)
        def run(args):
            self.run(*args, capture_output=False, exit=True)


class ResticPlan(Component):
    class Props:
        repository = Prop(ResticRepository)
        precommands = Prop(list, default=[])
        paths = Prop(list, default=[], lazy=True)
        exclude = Prop(list, default=[], lazy=True)
        preamble = Prop(str, default=BASH_PREAMBLE)

    @lazy_property
    def backup_script_content(self):
        out = StringIO()
        out.write(self.props.preamble)

        for cmd in self.props.precommands:
            out.write(f"{cmd}\n")

        for key, value in self.props.repository.extra_env.items():
            out.write(f"export {key}={quote(value)}\n")

        cmd = ["exec", "restic", "backup"]
        cmd += [quote(str(path)) for path in evaluate(self.props.paths)]
        cmd += [
            f"--exclude={quote(str(path))}" for path in evaluate(self.props.exclude)
        ]
        out.write(f"{' '.join(cmd)}\n")

        return out.getvalue()

    def backup_script(self, directory, name):
        return directory.file(
            name=name,
            content=self.backup_script_content,
            mode="700",
        )
