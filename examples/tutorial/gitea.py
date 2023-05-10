from collections.abc import Callable
from typing import Optional

import yaml
from opslib import Component, Directory, Prop, lazy_property


class Gitea(Component):
    class Props:
        directory = Prop(Directory)
        listen = Prop(Optional[str])
        sidecar = Prop(Optional[Callable])

    def build(self):
        self.directory = self.props.directory
        self.data_volume = self.directory / "data"

        self.compose_file = self.directory.file(
            name="docker-compose.yml",
            content=self.compose_content,
        )

        self.compose_up = self.directory.host.command(
            args=[*self.compose_args, "up", "-d"],
            run_after=[self.compose_file],
        )

    @lazy_property
    def compose_content(self):
        content = dict(
            version="3",
            services=dict(
                app=dict(
                    image="gitea/gitea:1.19.0",
                    volumes=[
                        f"{self.data_volume.path}:/data",
                    ],
                    restart="unless-stopped",
                ),
            ),
        )

        if self.props.listen:
            content["services"]["app"]["ports"] = [
                f"{self.props.listen}:3000",
            ]

        if self.props.sidecar:
            content["services"]["sidecar"] = self.props.sidecar("http://app:3000")

        return yaml.dump(content, sort_keys=False)

    @property
    def compose_args(self):
        return ["docker", "compose", "--project-directory", self.directory.path]

    def add_commands(self, cli):
        @cli.forward_command
        def compose(args):
            """Run `docker compose` with the given arguments"""
            self.directory.host.run(
                *[*self.compose_args, *args],
                capture_output=False,
                exit=True,
            )
