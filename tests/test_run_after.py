import pytest

from opslib.operations import apply
from opslib.places import LocalHost
from opslib.props import Prop


@pytest.fixture
def local_host():
    return LocalHost()


def test_none(tmp_path, local_host, stack):
    path = tmp_path / "file"
    stack.cmd = local_host.command(args=["touch", path])

    apply(stack, deploy=True)
    assert path.is_file()
    path.unlink()
    apply(stack, deploy=True)
    assert path.is_file()


def test_file(tmp_path, local_host, TestingStack):
    out_path = tmp_path / "output"

    class Bench(TestingStack):
        class Props:
            content = Prop(str)

        def build(self):
            self.file = local_host.directory(tmp_path).file(
                name="input",
                content=self.props.content,
            )

            self.cmd = local_host.command(
                args=["cp", self.file.path, out_path],
                run_after=[self.file],
            )

    out_path.write_text("initial")

    # command not run because `file` not deployed
    apply(Bench(content="two").cmd, deploy=True)
    assert out_path.read_text() == "initial"

    # command run because `file` is being deployed
    apply(Bench(content="two"), deploy=True)
    assert out_path.read_text() == "two"

    out_path.write_text("final")
    # command not run because `file` did not change
    apply(Bench(content="two"), deploy=True)
    assert out_path.read_text() == "final"


def test_command(tmp_path, local_host, TestingStack):
    mid_path = tmp_path / "middle"
    out_path = tmp_path / "output"

    class Bench(TestingStack):
        class Props:
            content = Prop(str)

        def build(self):
            self.file = local_host.directory(tmp_path).file(
                name="input",
                content=self.props.content,
            )

            self.pre_cmd = local_host.command(
                args=["cp", self.file.path, mid_path],
                run_after=[self.file],
            )

            self.cmd = local_host.command(
                args=["cp", mid_path, out_path],
                run_after=[self.pre_cmd],
            )

    out_path.write_text("initial")

    # command not run because `pre_cmd` not run
    apply(Bench(content="two").cmd, deploy=True)
    assert out_path.read_text() == "initial"

    # command run because `pre_cmd` is being run
    apply(Bench(content="two"), deploy=True)
    assert out_path.read_text() == "two"

    out_path.write_text("final")
    # command not run because `pre_cmd` did not run
    apply(Bench(content="two"), deploy=True)
    assert out_path.read_text() == "final"
