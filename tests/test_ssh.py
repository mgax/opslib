from pathlib import Path

import pytest

from opslib.operations import apply


@pytest.mark.slow
def test_ssh_run(ssh_container):
    result = ssh_container.run("id")
    assert not result.failed
    assert result.stdout == "uid=1000(opslib) gid=1000(opslib) groups=1000(opslib)\n"
    assert result.stderr == ""


@pytest.mark.slow
def test_ansible_ssh(ssh_container, stack):
    stack.foo = ssh_container.file(
        path=Path("/tmp/foo.txt"),
        content="hello world",
    )

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
def test_ansible_sudo(ssh_container, stack):
    stack.foo = ssh_container.sudo().file(
        path=Path("/tmp/foo.txt"),
        content="hello world",
    )

    apply(stack, deploy=True)

    assert ssh_container.run("stat -c %U /tmp/foo.txt").stdout == "root\n"


@pytest.mark.slow
def test_command(ssh_container, stack):
    stack.cat = ssh_container.command(
        args=["bash -c 'id; pwd'"],
    )
    assert stack.cat.run().output == (
        "uid=1000(opslib) gid=1000(opslib) groups=1000(opslib)\n/home/opslib\n"
    )


@pytest.mark.slow
def test_command_sudo(ssh_container, stack):
    stack.cat = ssh_container.sudo().command(
        args=["bash -c 'id; pwd'"],
    )
    assert stack.cat.run().output == (
        "uid=0(root) gid=0(root) groups=0(root)\n/home/opslib\n"
    )


@pytest.mark.slow
def test_command_cwd(ssh_container, stack):
    stack.foo = ssh_container.directory("/home/opslib/foo")
    stack.cat = stack.foo.command(
        args=["bash -c 'id; pwd'"],
    )
    apply(stack, deploy=True)
    assert stack.cat.run().output == (
        "uid=1000(opslib) gid=1000(opslib) groups=1000(opslib)\n/home/opslib/foo\n"
    )


@pytest.mark.slow
def test_command_sudo_cwd(ssh_container, stack):
    stack.foo = ssh_container.directory("/home/opslib/foo")
    stack.cat = ssh_container.sudo().command(
        args=["bash -c 'id; pwd'"],
        cwd=stack.foo.path,
    )
    apply(stack, deploy=True)
    assert stack.cat.run().output == (
        "uid=0(root) gid=0(root) groups=0(root)\n/home/opslib/foo\n"
    )


@pytest.mark.slow
def test_command_space_in_cwd_fails(ssh_container, stack):
    stack.foo = ssh_container.directory("/home/opslib/foo bar")
    stack.cat = stack.foo.command(
        args=["bash -c 'id; pwd'"],
    )
    with pytest.raises(ValueError) as error:
        apply(stack, deploy=True)

    assert error.value.args == ("CWD must not contain special characters",)
