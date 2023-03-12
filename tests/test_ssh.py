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


@pytest.mark.slow
def test_run_sudo(docker_ssh):
    result = docker_ssh.sudo().run("id")
    assert not result.failed
    assert result.stdout.startswith("uid=0(root) gid=0(root) groups=0(root)")
    assert result.stderr == ""


@pytest.mark.slow
def test_run_sudo_with_input(docker_ssh):
    result = docker_ssh.sudo().run(input="id\n")
    assert not result.failed
    assert result.stdout.startswith("uid=0(root) gid=0(root) groups=0(root)")
    assert result.stderr == ""


@pytest.mark.slow
def test_ansible_sudo(docker_ssh):
    stack = Stack()
    stack.foo = docker_ssh.sudo().file(
        path=Path("/tmp/foo.txt"),
        content="hello world",
    )

    apply(stack, deploy=True)

    assert docker_ssh.run("stat -c %U /tmp/foo.txt").stdout == "root\n"
