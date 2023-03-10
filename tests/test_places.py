import pytest

from opslib.operations import apply
from opslib.places import LocalHost
from opslib.things import Stack


@pytest.fixture
def local_host():
    return LocalHost()


def test_file_from_path(tmp_path, local_host):
    path = tmp_path / "foo.txt"
    stack = Stack()
    stack.foo = local_host.file(
        path=path,
        content="hello foo",
    )

    apply(stack, deploy=True)

    with path.open() as f:
        assert f.read() == "hello foo"


def test_directory_from_path(tmp_path, local_host):
    path = tmp_path / "foo"
    stack = Stack()
    stack.foo = local_host.directory(
        path=path,
    )

    apply(stack, deploy=True)

    assert path.is_dir()


def test_subdir(tmp_path, local_host):
    path = tmp_path / "foo"
    stack = Stack()
    stack.foo = local_host.directory(
        path=path,
    )
    stack.bar = stack.foo.subdir("bar")

    apply(stack, deploy=True)

    assert (path / "bar").is_dir()


def test_file_from_directory(tmp_path, local_host):
    path = tmp_path / "foo.txt"
    stack = Stack()
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
