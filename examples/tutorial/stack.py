from pathlib import Path

import click
import yaml

from opslib.places import Directory, LocalHost
from opslib.props import Prop
from opslib.things import Stack, Thing


class Gitea(Thing):
    class Props:
        directory = Prop(Directory)

    def build(self):
        self.directory = self.props.directory
        self.data_volume = self.directory / "data"

        self.compose_file = self.directory.file(
            name="docker-compose.yml",
            content=self.compose_file_content,
        )

        self.compose_up = self.directory.host.command(
            args=[*self.compose_args, "up", "-d"],
        )

    @property
    def compose_args(self):
        return ["docker", "compose", "--project-directory", self.directory.path]

    @property
    def compose_file_content(self):
        content = dict(
            version="3",
            services=dict(
                app=dict(
                    image="gitea/gitea:1.19.0",
                    volumes=[
                        f"{self.data_volume.path}:/data",
                    ],
                    restart="unless-stopped",
                    ports=[
                        "127.0.0.1:3000:3000",
                    ],
                ),
            ),
        )
        return yaml.dump(content, sort_keys=False)

    def add_commands(self, cli):
        @cli.command(context_settings=dict(ignore_unknown_options=True))
        @click.argument("args", nargs=-1, type=click.UNPROCESSED)
        def compose(args):
            """Run `docker compose` with the given arguments"""
            self.directory.host.run(
                *[*self.compose_args, *args],
                capture_output=False,
                exit=True,
            )


class MyCodeForge(Stack):
    def build(self):
        host = LocalHost()
        repo = host.directory(Path(__file__).parent)

        self.gitea = Gitea(
            directory=repo / "localgitea",
        )


def get_stack():
    return MyCodeForge()
