import configparser
import io
from pathlib import Path
from typing import Optional, Union

import click

from opslib.components import Component
from opslib.lazy import evaluate, lazy_property
from opslib.places import BaseHost
from opslib.props import Prop


def render_unit_file(contents):
    config = configparser.ConfigParser()
    config.optionxform = str
    config.update(contents)
    out = io.StringIO()
    config.write(out, space_around_delimiters=False)
    return out.getvalue()


class SystemdUnit(Component):
    class Props:
        host = Prop(BaseHost)
        name = Prop(str)
        contents = Prop(dict, lazy=True)

    @lazy_property
    def unit_file_content(self):
        return render_unit_file(evaluate(self.props.contents))

    def build(self):
        self.unit_file = self.props.host.file(
            path=Path("/etc/systemd/system") / self.props.name,
            content=self.unit_file_content,
        )

    def enable_command(self, now=False):
        return self.props.host.command(
            args=["systemctl", "enable", *(["--now"] if now else []), self.props.name],
            run_after=[self.unit_file],
        )

    def start_command(self):
        return self.props.host.command(
            args=["systemctl", "start", self.props.name],
            run_after=[self.unit_file],
        )

    def add_commands(self, cli):
        @cli.forward_command
        @click.argument("command")
        def systemctl(command, args):
            self.props.host.run(
                "env",
                "SYSTEMD_COLORS=1",
                "systemctl",
                command,
                self.props.name,
                *args,
                capture_output=False,
                exit=True,
            )

        @cli.forward_command
        def journalctl(args):
            self.props.host.run(
                "journalctl", "-u", self.props.name, *args, capture_output=False
            )


class SystemdTimerService(Component):
    class Props:
        host = Prop(BaseHost)
        name = Prop(str)
        on_calendar = Prop(str)
        timeout_start_sec = Prop(str)
        exec_start = Prop(Union[str, Path], lazy=True)
        user = Prop(Optional[str])
        group = Prop(Optional[str])

    def build(self):
        service_fields = {}

        if self.props.user:
            service_fields["User"] = self.props.user

        if self.props.group:
            service_fields["Group"] = self.props.group

        self.service = SystemdUnit(
            host=self.props.host,
            name=f"{self.props.name}.service",
            contents=dict(
                Service=dict(
                    Type="oneshot",
                    TimeoutStartSec=self.props.timeout_start_sec,
                    ExecStart=self.props.exec_start,
                    **service_fields,
                ),
            ),
        )

        self.timer = SystemdUnit(
            host=self.props.host,
            name=f"{self.props.name}.timer",
            contents=dict(
                Timer=dict(
                    OnCalendar=self.props.on_calendar,
                ),
                Install=dict(
                    WantedBy="timers.target",
                ),
            ),
        )

        self.enable = self.timer.enable_command(now=True)
