import json
from hashlib import sha256

import pytest
from click.testing import CliRunner

from opslib.cli import get_main_cli
from opslib.components import init_statedir
from opslib.lazy import NotAvailable, evaluate
from opslib.operations import apply
from opslib.terraform import TerraformProvider, TerraformResource


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


def test_diff(local_stack, capsys):
    stack = local_stack()
    results = apply(stack, deploy=True, dry_run=True)
    assert not stack.path.exists()
    captured = capsys.readouterr()
    assert results[stack.file].changed
    assert "# local_file.thing will be created" in captured.out
    assert '+ resource "local_file" "thing"' in captured.out
    assert '+ content              = "world"' in captured.out
    assert f'+ filename             = "{stack.path}"' in captured.out


@pytest.mark.parametrize("different", [True, False])
def test_refresh(local_stack, different):
    stack = local_stack()
    apply(stack, deploy=True)
    stack.path.write_text("different" if different else "world")
    apply(stack, refresh=True)
    results = apply(stack, deploy=True, dry_run=True)
    assert results[stack.file].changed == different


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


def test_output(local_stack):
    stack = local_stack(output=["content_sha256"])
    apply(stack, deploy=True)
    assert evaluate(stack.file.output["content_sha256"]) == sha256(b"world").hexdigest()


def test_output_not_available(Stack):
    stack = Stack()
    stack.provider = TerraformProvider(
        name="consul",
    )
    stack.order = stack.provider.resource(
        type="consul_service",
        body=dict(
            name="foo",
            node="bar",
        ),
        output=["service_id"],
    )
    init_statedir(stack)
    apply(stack, refresh=True)
    with pytest.raises(NotAvailable) as error:
        print(evaluate(stack.order.output["service_id"]))

    assert error.value.args == (
        "<TerraformResource order>: output 'service_id' not available",
    )


def test_import_resource(Stack):
    stack = Stack()
    stack.time = TerraformResource(
        type="time_static",
        body={},
        output=["id"],
    )
    init_statedir(stack)
    value = "2020-02-12T06:36:13Z"
    stack.time.import_resource(value)
    assert evaluate(stack.time.output["id"]) == value


def test_provider_config(Stack, tmp_path):
    stack = Stack()
    stack.provider = TerraformProvider(
        name="tfcoremock",
        source="tfcoremock",
        config=dict(
            resource_directory="opslib_resource_directory",
        ),
    )
    stack.resource = stack.provider.resource(
        type="tfcoremock_simple_resource",
        body=dict(
            number=13,
        ),
    )
    init_statedir(stack)
    apply(stack, deploy=True)
    # XXX for some reason, Terraform quotes our directory name
    [outfile] = (stack.resource.tf_path / '"opslib_resource_directory"').iterdir()
    assert json.loads(outfile.read_text())["values"]["number"]["number"] == "13"
