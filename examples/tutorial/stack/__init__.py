import os
from pathlib import Path

from opslib.components import Stack
from opslib.places import LocalHost

from .gitea import Gitea
from .hetzner import VPS

stack = Stack(__name__)

if os.environ.get("MYCODEFORGE_VPS") == "yes":
    stack.vps = VPS(name="mycodeforge")
    stack.directory = stack.vps.host.directory("/opt/opslib")

else:
    stack.host = LocalHost()
    stack.directory = stack.host.directory(Path(__file__).parent.parent / "target")

stack.gitea = Gitea(
    directory=stack.directory / "gitea",
    listen="3000",
)
