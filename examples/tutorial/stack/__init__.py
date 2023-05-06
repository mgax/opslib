import os
from pathlib import Path

from opslib.components import Stack
from opslib.places import LocalHost

from .gitea import Gitea
from .hetzner import VPS


class MyCodeForge(Stack):
    def build(self):
        if os.environ.get("MYCODEFORGE_VPS") == "yes":
            self.vps = VPS(name="mycodeforge")
            self.directory = self.vps.host.directory("/opt/opslib")

        else:
            self.host = LocalHost()
            self.directory = self.host.directory(
                Path(__file__).parent.parent / "target"
            )

        self.gitea = Gitea(
            directory=self.directory / "gitea",
            listen="3000",
        )


def get_stack():
    return MyCodeForge()
