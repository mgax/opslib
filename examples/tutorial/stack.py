import os
from pathlib import Path

from opslib import Component, LocalHost, Stack

from cloudflare import Cloudflare
from gitea import Gitea
from hetzner import VPS


class Local(Component):
    def build(self):
        self.host = LocalHost()
        self.directory = self.host.directory(Path(__file__).parent / "target")
        self.gitea = Gitea(
            directory=self.directory / "gitea",
            listen="127.0.0.1:3000",
        )


class Cloud(Component):
    def build(self):
        self.cloudflare = Cloudflare(
            zone_name=os.environ["CLOUDFLARE_ZONE_NAME"],
            record_name=os.environ.get("CLOUDFLARE_RECORD_NAME", "example-gitea"),
            tunnel_secret=os.environ["CLOUDFLARE_TUNNEL_SECRET"],
        )
        self.vps = VPS(
            name="opslib-tutorial",
        )
        self.gitea = Gitea(
            directory=self.vps.host.directory("/opt/gitea"),
            sidecar=self.cloudflare.sidecar,
        )


stack = Stack(__name__)
stack.local = Local()
stack.cloud = Cloud()
