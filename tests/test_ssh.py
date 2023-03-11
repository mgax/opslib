from pathlib import Path

import pytest

from opslib.operations import apply
from opslib.things import Stack


@pytest.mark.slow
def test_ssh_run(docker_ssh):
    result = docker_ssh.run("id")
    assert not result.failed
    assert result.stdout == "uid=1000(opslib) gid=1000(opslib) groups=1000(opslib)\n"
    assert result.stderr == ""


@pytest.mark.slow
def test_ansible_ssh(docker_ssh):
    stack = Stack()
    stack.foo = docker_ssh.file(
        path=Path("/tmp/foo.txt"),
        content="hello world",
    )

    apply(stack, deploy=True)

    assert docker_ssh.run("cat /tmp/foo.txt").stdout == "hello world"
