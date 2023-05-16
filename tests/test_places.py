import shlex
from textwrap import dedent

import pytest
from click.testing import CliRunner

from opslib.cli import get_cli
from opslib.lazy import Lazy
from opslib.operations import apply
from opslib.places import LocalHost


@pytest.fixture
def local_host():
    return LocalHost()


def test_file_from_path(tmp_path, local_host, stack):
    path = tmp_path / "foo.txt"
    stack.foo = local_host.file(
        path=path,
        content="hello foo",
    )

    apply(stack, deploy=True)

    with path.open() as f:
        assert f.read() == "hello foo"


def test_file_lazy_content(tmp_path, local_host, stack):
    path = tmp_path / "foo.txt"
    called = False

    def get_content():
        nonlocal called
        called = True
        return "hello world"

    stack.foo = local_host.file(
        path=path,
        content=Lazy(get_content),
    )

    assert not called
    apply(stack, deploy=True)
    assert called

    with path.open() as f:
        assert f.read() == "hello world"


def test_directory_from_path(tmp_path, local_host, stack):
    path = tmp_path / "foo"
    stack.foo = local_host.directory(
        path=path,
    )

    apply(stack, deploy=True)

    assert path.is_dir()


def test_directory_from_string_path(tmp_path, local_host, stack):
    path = tmp_path / "foo"
    stack.foo = local_host.directory(str(path))

    apply(stack, deploy=True)

    assert path.is_dir()


def test_subdir(tmp_path, local_host, stack):
    path = tmp_path / "foo"
    stack.foo = local_host.directory(
        path=path,
    )
    stack.bar = stack.foo.subdir("bar")

    apply(stack, deploy=True)

    assert (path / "bar").is_dir()


def test_truediv(tmp_path, local_host, stack):
    path = tmp_path / "foo"
    stack.foo = local_host.directory(
        path=path,
    )
    stack.bar = stack.foo / "bar"

    apply(stack, deploy=True)

    assert (path / "bar").is_dir()


def test_file_from_directory(tmp_path, local_host, stack):
    path = tmp_path / "foo.txt"
    stack.foo = local_host.directory(
        path=path,
    )
    stack.bar = stack.foo.file(
        name="bar",
        content="hello bar",
    )

    apply(stack, deploy=True)

    with (path / "bar").open() as f:
        assert f.read() == "hello bar"


def test_command(tmp_path, local_host, stack):
    path = tmp_path / "foo"
    stack.foo = local_host.command(
        args=["touch", str(path)],
    )

    apply(stack, deploy=True)

    assert path.is_file()


def test_command_with_input(tmp_path, local_host, stack):
    stack.foo = local_host.command(
        input=dedent(
            f"""\
            cd {shlex.quote(str(tmp_path))}
            touch foo
            """
        ),
    )

    apply(stack, deploy=True)

    assert (tmp_path / "foo").is_file()


def test_command_cli_run(tmp_path, local_host, stack):
    path = tmp_path / "file"
    stack.foo = local_host.command(
        args=["touch", path],
    )
    cli = get_cli(stack.foo)
    result = CliRunner().invoke(cli, ["run"], catch_exceptions=False)
    assert result.exit_code == 0
    assert path.is_file()


def test_directory_command_localhost_cwd(tmp_path, local_host, stack):
    stack.directory = local_host.directory(tmp_path / "here")
    stack.foo = stack.directory.command(
        args=["pwd"],
    )
    apply(stack, deploy=True)

    assert stack.foo.run().output.strip() == str(tmp_path / "here")


def test_directory_run_localhost_cwd(tmp_path, local_host, stack):
    stack.directory = local_host.directory(tmp_path / "here")
    apply(stack, deploy=True)
    assert stack.directory.run("pwd").output.strip() == str(tmp_path / "here")


def test_file_content_diff(tmp_path, local_host, capsys, stack):
    foo_path = tmp_path / "foo.txt"
    with foo_path.open("w") as f:
        f.write("hello\nworld\n")

    stack.foo = local_host.file(
        path=foo_path,
        content="hello\nthere\n",
    )

    apply(stack, deploy=True, dry_run=True)

    captured = capsys.readouterr()
    assert captured.out == dedent(
        f"""\
        foo.action AnsibleAction ...
        foo.action AnsibleAction [changed]
        --- {foo_path}
        +++ {foo_path}
        @@ -1,2 +1,2 @@
         hello
        -world
        +there

        """
    )
    assert captured.err == ""

    with foo_path.open() as f:
        assert f.read() == "hello\nworld\n", "Target file must not change"


def test_file_mode_diff(tmp_path, local_host, capsys, stack):
    foo_path = tmp_path / "foo.txt"
    foo_path.touch(mode=0o644)

    stack.foo = local_host.file(
        path=foo_path,
        content="",
        mode="755",
    )

    apply(stack, deploy=True, dry_run=True)

    captured = capsys.readouterr()
    assert captured.out == dedent(
        f"""\
        foo.action AnsibleAction ...
        foo.action AnsibleAction [changed]
        --- {foo_path}
        +++ {foo_path}
        @@ -1 +1 @@
        -{{'path': {str(foo_path)!r}, 'mode': '0644'}}
        +{{'path': {str(foo_path)!r}, 'mode': '0755'}}

        """
    )
    assert captured.err == ""

    assert (foo_path.stat().st_mode & 0xFFF) == 0o644
