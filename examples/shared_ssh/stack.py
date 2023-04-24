import os

from opslib.components import Stack
from opslib.places import SshHost


class Bench(Stack):
    def build(self):
        host = SshHost(
            hostname=os.environ["REMOTE"],
            control_socket=os.environ.get("CONTROL_SOCKET"),
        )

        for n in range(10):
            command = host.command(args=["pwd"])
            setattr(self, f"command_{n}", command)


def get_stack():
    return Bench()
