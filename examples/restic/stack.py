import os
from pathlib import Path

from opslib.components import Stack
from opslib.extras.restic import ResticRepository
from opslib.places import LocalHost

stack = Stack(__name__)
stack.host = LocalHost()
stack.directory = stack.host.directory(Path(__file__).parent / "demo")
stack.repo = stack.directory / "repo"
stack.target = stack.directory / "target"

stack.restic = ResticRepository(
    repository=str(stack.repo.path),
    password=os.environ["RESTIC_PASSWORD"],
)

stack.plan = stack.restic.plan(
    precommands=[
        f"fortune > {stack.target.path}/wisdom.txt",
    ],
    paths=[
        stack.target.path,
    ],
)

stack.backup_script = stack.plan.backup_script(
    directory=stack.directory,
    name="backup",
)
