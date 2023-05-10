from pathlib import Path

import yaml

from opslib.components import Component, Stack
from opslib.places import Directory, LocalHost
from opslib.props import Prop

PATH = Path(__file__).parent


class App(Component):
    class Props:
        directory = Prop(Directory)
        listen = Prop(str)

    def build(self):
        self.directory = self.props.directory

        self.nginx_conf = self.directory.file(
            name="nginx.conf",
            content=(PATH / "nginx.conf").read_text(),
        )

        self.dockerfile = self.directory.file(
            name="Dockerfile",
            content=(PATH / "Dockerfile").read_text(),
        )

        self.app_py = self.directory.file(
            name="app.py",
            content=(PATH / "app.py").read_text(),
        )

        self.compose_file = self.directory.file(
            name="docker-compose.yml",
            content=self.compose_file_content,
        )

        self.compose_build = self.directory.host.command(
            args=[*self.compose_args, "build", "--pull"],
            run_after=[
                self.dockerfile,
                self.app_py,
            ],
        )

        self.compose_pull = self.directory.host.command(
            args=[*self.compose_args, "pull"],
            run_after=[
                self.compose_file,
            ],
        )

        self.compose_up = self.directory.host.command(
            args=[*self.compose_args, "up", "-d", "-t1"],
            run_after=[
                self.compose_file,
                self.compose_build,
            ],
        )

        self.nginx_restart = self.directory.host.command(
            args=[*self.compose_args, "restart", "nginx"],
            run_after=[
                self.nginx_conf,
            ],
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
                    build=".",
                    restart="unless-stopped",
                ),
                nginx=dict(
                    image="nginx",
                    volumes=[
                        "./nginx.conf:/etc/nginx/nginx.conf:ro",
                    ],
                    ports=[
                        "8080:80",
                    ],
                    restart="unless-stopped",
                ),
            ),
        )
        return yaml.dump(content, sort_keys=False)

    def add_commands(self, cli):
        @cli.forward_command
        def compose(args):
            """Run `docker compose` with the given arguments"""
            self.directory.host.run(
                *[*self.compose_args, *args],
                capture_output=False,
                exit=True,
            )


stack = Stack(__name__)
stack.host = LocalHost()
stack.directory = stack.host.directory(Path(__file__).parent / "target")
stack.app = App(
    directory=stack.directory / "opslib-examples-compose",
    listen="3000",
)
