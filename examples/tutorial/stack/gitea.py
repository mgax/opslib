import click
import yaml

from opslib.components import Component
from opslib.places import Directory
from opslib.props import Prop


class Gitea(Component):
    class Props:
        directory = Prop(Directory)
        listen = Prop(str)

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
                        f"{self.props.listen}:3000",
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
