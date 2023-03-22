from pathlib import Path

from opslib.places import LocalHost
from opslib.things import Stack

from .gitea import Gitea


class MyCodeForge(Stack):
    def build(self):
        host = LocalHost()
        target_path = Path(__file__).parent.parent / "target"
        self.directory = host.directory(target_path)

        self.gitea = Gitea(
            directory=self.directory / "gitea",
            listen="3000",
        )


def get_stack():
    return MyCodeForge()
