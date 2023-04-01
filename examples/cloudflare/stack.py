import json
import os
from base64 import b64encode
from collections.abc import Callable
from pathlib import Path

import click
import yaml

from opslib.components import Component, Stack
from opslib.lazy import evaluate, lazy_property
from opslib.places import Directory, LocalHost
from opslib.props import Prop
from opslib.terraform import TerraformProvider

NGINX_CONF = """\
worker_processes  1;
events { worker_connections  1024; }

http {
  server {
    listen 80 default_server;
    location / {
        return 200 '<span style="font-size:120px">&#x1F44D;';
        add_header Content-Type text/html;
    }
  }
}
"""


class Cloudflare(Component):
    class Props:
        account_id = Prop(str)
        zone_id = Prop(str)
        name = Prop(str)
        secret = Prop(str)

    def build(self):
        self.provider = TerraformProvider(
            name="cloudflare",
            source="cloudflare/cloudflare",
            version="~> 4.2",
        )

        self.tunnel = self.provider.resource(
            type="cloudflare_tunnel",
            body=dict(
                account_id=self.props.account_id,
                name=self.props.name,
                secret=self.props.secret,
            ),
            output=["id"],
        )

        self.cname = self.provider.resource(
            type="cloudflare_record",
            body=dict(
                zone_id=self.props.zone_id,
                name=self.props.name,
                type="CNAME",
                value=self.cname_value,
                proxied=True,
            ),
        )

    @lazy_property
    def cname_value(self):
        return f"{evaluate(self.tunnel.output['id'])}.cfargotunnel.com"

    def token(self):
        payload = {
            "a": evaluate(self.props.account_id),
            "t": evaluate(self.tunnel.output["id"]),
            "s": self.props.secret,
        }
        return b64encode(json.dumps(payload).encode("utf8")).decode("utf8")

    def sidecar(self, url):
        return dict(
            image="cloudflare/cloudflared",
            command=f"tunnel --no-autoupdate run --token {self.token()} --url {url}",
            restart="unless-stopped",
        )


class App(Component):
    class Props:
        directory = Prop(Directory)
        sidecar = Prop(Callable, lazy=True)

    def build(self):
        self.directory = self.props.directory

        self.nginx_conf = self.directory.file(
            name="nginx.conf",
            content=NGINX_CONF,
        )

        self.compose_file = self.directory.file(
            name="docker-compose.yml",
            content=self.compose_file_content,
        )

        self.compose_up = self.directory.host.command(
            args=[*self.compose_args, "up", "-d", "-t1"],
            run_after=[self.compose_file],
        )

    @property
    def compose_args(self):
        return ["docker", "compose", "--project-directory", self.directory.path]

    @lazy_property
    def compose_file_content(self):
        content = dict(
            version="3",
            services=dict(
                nginx=dict(
                    image="nginx",
                    volumes=[
                        "./nginx.conf:/etc/nginx/nginx.conf:ro",
                    ],
                    restart="unless-stopped",
                ),
                sidecar=self.props.sidecar("http://nginx"),
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


class Demo(Stack):
    def build(self):
        host = LocalHost()
        self.directory = host.directory(Path(__file__).parent / "target")

        self.cloudflare = Cloudflare(
            account_id=os.environ["CLOUDFLARE_ACCOUNT_ID"],
            zone_id=os.environ["CLOUDFLARE_ZONE_ID"],
            name=os.environ["CLOUDFLARE_TUNNEL_NAME"],
            secret=b64encode(
                os.environ["CLOUDFLARE_TUNNEL_SECRET"].encode("utf8")
            ).decode("utf8"),
        )

        self.app = App(
            directory=self.directory / "app",
            sidecar=self.cloudflare.sidecar,
        )


def get_stack():
    return Demo()
