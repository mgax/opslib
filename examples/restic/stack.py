import os
from pathlib import Path

from opslib.components import Stack
from opslib.extras.restic import ResticRepository
from opslib.places import LocalHost


class Demo(Stack):
    def build(self):
        host = LocalHost()
        self.directory = host.directory(Path(__file__).parent / "demo")
        self.repo = self.directory / "repo"
        self.target = self.directory / "target"

        self.restic = ResticRepository(
            repository=str(self.repo.path),
            password=os.environ["RESTIC_PASSWORD"],
        )

        self.plan = self.restic.plan(
            precommands=[
                f"fortune > {self.target.path}/wisdom.txt",
            ],
            paths=[
                self.target.path,
            ],
        )

        self.backup_script = self.plan.backup_script(
            directory=self.directory,
            name="backup",
        )


def get_stack():
    return Demo()
