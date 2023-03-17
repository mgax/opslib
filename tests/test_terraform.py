from pathlib import Path

import pytest
from click.testing import CliRunner

from opslib.cli import get_main_cli
from opslib.operations import apply
from opslib.props import Prop
from opslib.terraform import TerraformProvider
from opslib.things import init_statedir


@pytest.fixture
def Bench(Stack):
    class Bench(Stack):
        class Props:
            path = Prop(Path)

        def build(self):
            self.provider = TerraformProvider(
                name="local",
                source="hashicorp/local",
                version="~> 2.3",
            )

            self.file = self.provider.resource(
                type="local_file",
                body=dict(
                    content="world",
                    filename=str(self.props.path),
                ),
            )

    return Bench


def test_deploy(Bench, tmp_path):
    path = tmp_path / "hello.txt"
    stack = Bench(path=path)

    init_statedir(stack)
    results = apply(stack, deploy=True)
    assert results[stack.file].changed
    assert path.read_text() == "world"

    results = apply(stack, deploy=True)
    assert not results[stack.file].changed


def test_cli(Bench, tmp_path, capfd):
    path = tmp_path / "hello.txt"
    stack = Bench(path=path)
    init_statedir(stack)
    cli = get_main_cli(lambda: stack)
    capfd.readouterr()
    CliRunner().invoke(cli, ["file", "terraform", "plan"], catch_exceptions=False)
    captured = capfd.readouterr()
    assert "Terraform will perform the following actions:" in captured.out
