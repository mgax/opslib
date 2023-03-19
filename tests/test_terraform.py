import pytest
from click.testing import CliRunner

from opslib.cli import get_main_cli
from opslib.operations import apply
from opslib.terraform import TerraformProvider
from opslib.things import init_statedir


@pytest.fixture
def local_stack(Stack, tmp_path):
    def create_local_stack(**file_props):
        path = tmp_path / "hello.txt"
        file_props.setdefault("type", "local_file")
        file_props.setdefault("body", dict(content="world", filename=str(path)))

        class LocalStack(Stack):
            def build(self):
                self.provider = TerraformProvider(
                    name="local",
                    source="hashicorp/local",
                    version="~> 2.3",
                )

                self.path = path

                self.file = self.provider.resource(**file_props)

        stack = LocalStack()
        init_statedir(stack)
        return stack

    return create_local_stack


def test_deploy(local_stack):
    stack = local_stack()
    results = apply(stack, deploy=True)
    assert results[stack.file].changed
    assert stack.path.read_text() == "world"

    results = apply(stack, deploy=True)
    assert not results[stack.file].changed


def test_cli(local_stack, capfd):
    cli = get_main_cli(local_stack)
    capfd.readouterr()
    CliRunner().invoke(cli, ["file", "terraform", "plan"], catch_exceptions=False)
    captured = capfd.readouterr()
    assert "Terraform will perform the following actions:" in captured.out


def test_no_global_plugin_cache(local_stack, monkeypatch):
    monkeypatch.delenv("TF_PLUGIN_CACHE_DIR", raising=False)
    stack = local_stack()
    apply(stack, deploy=True)

    [version] = (
        stack.file.tf_path
        / ".terraform/providers/registry.terraform.io/hashicorp/local"
    ).iterdir()
    [arch] = version.iterdir()
    assert arch.is_symlink()

    assert arch.readlink() == (
        stack.provider.plugin_cache_path
        / "registry.terraform.io/hashicorp/local"
        / version.name
        / arch.name
    )
