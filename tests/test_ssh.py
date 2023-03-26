from pathlib import Path

import pytest

from opslib.components import init_statedir
from opslib.operations import apply


@pytest.mark.slow
def test_ssh_run(ssh_container):
    result = ssh_container.run("id")
    assert not result.failed
    assert result.stdout == "uid=1000(opslib) gid=1000(opslib) groups=1000(opslib)\n"
    assert result.stderr == ""


@pytest.mark.slow
def test_ansible_ssh(ssh_container, Stack):
    stack = Stack()
    stack.foo = ssh_container.file(
        path=Path("/tmp/foo.txt"),
        content="hello world",
    )

    init_statedir(stack)
    apply(stack, deploy=True)

    assert ssh_container.run("cat /tmp/foo.txt").stdout == "hello world"


@pytest.mark.slow
def test_run_sudo(ssh_container):
    result = ssh_container.sudo().run("id")
    assert not result.failed
    assert result.stdout.startswith("uid=0(root) gid=0(root) groups=0(root)")
    assert result.stderr == ""


@pytest.mark.slow
def test_run_sudo_with_input(ssh_container):
    result = ssh_container.sudo().run(input="id\n")
    assert not result.failed
    assert result.stdout.startswith("uid=0(root) gid=0(root) groups=0(root)")
    assert result.stderr == ""


@pytest.mark.slow
def test_ansible_sudo(ssh_container, Stack):
    stack = Stack()
    stack.foo = ssh_container.sudo().file(
        path=Path("/tmp/foo.txt"),
        content="hello world",
    )

    init_statedir(stack)
    apply(stack, deploy=True)

    assert ssh_container.run("stat -c %U /tmp/foo.txt").stdout == "root\n"
