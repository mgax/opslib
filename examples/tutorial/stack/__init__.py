import os
from pathlib import Path

from opslib.components import Stack
from opslib.places import LocalHost
from opslib.props import Prop

from .gitea import Gitea
from .hetzner import Hetzner


class MyCodeForge(Stack):
    class Props:
        vps = Prop(bool)

    def build(self):
        if self.props.vps:
            self.hetzner = Hetzner(
                token=os.environ["HETZNER_TOKEN"],
                server_name="mycodeforge",
            )

            self.directory = self.hetzner.host.directory("/opt/opslib")

        else:
            host = LocalHost()
            self.directory = host.directory(Path(__file__).parent.parent / "target")

        self.gitea = Gitea(
            directory=self.directory / "gitea",
            listen="3000",
        )


def get_stack():
    return MyCodeForge(
        vps=os.environ.get("MYCODEFORGE_VPS") == "yes",
    )
