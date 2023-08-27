import json
from hashlib import sha256

import pytest
from click.testing import CliRunner

from opslib.cli import get_main_cli
from opslib.lazy import NotAvailable, evaluate
from opslib.operations import apply
from opslib.terraform import TerraformProvider, TerraformResource


@pytest.fixture
def local_stack(TestingStack, tmp_path):
    def create_local_stack(**file_props):
        path = tmp_path / "hello.txt"
        file_props.setdefault("type", "local_file")
        file_props.setdefault("args", dict(content="world", filename=str(path)))

        class LocalStack(TestingStack):
            def build(self):
                self.provider = TerraformProvider(
                    name="local",
                    source="hashicorp/local",
                    version="~> 2.3",
                )

                self.path = path

                self.file = self.provider.resource(**file_props)

        stack = LocalStack()
        return stack

    return create_local_stack


@pytest.mark.slow
def test_deploy(local_stack):
    stack = local_stack()
    results = apply(stack, deploy=True)
    assert results[stack.file].changed
    assert stack.path.read_text() == "world"

    results = apply(stack, deploy=True)
    assert not results[stack.file].changed


@pytest.mark.slow
def test_destroy(local_stack):
    stack = local_stack()
    results = apply(stack, deploy=True)
    assert stack.path.read_text() == "world"
    results = apply(stack, destroy=True)
    assert not stack.path.exists()
    assert results[stack.file].changed


@pytest.mark.slow
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


@pytest.mark.slow
@pytest.mark.parametrize("different", [True, False])
def test_refresh(local_stack, different):
    stack = local_stack()
    apply(stack, deploy=True)
    stack.path.write_text("different" if different else "world")
    apply(stack, refresh=True)
    results = apply(stack, deploy=True, dry_run=True)
    assert results[stack.file].changed == different


@pytest.mark.slow
def test_cli(local_stack, capfd):
    cli = get_main_cli(local_stack)
    capfd.readouterr()
    CliRunner().invoke(
        cli, ["file", "terraform", "plan"], obj={}, catch_exceptions=False
    )
    captured = capfd.readouterr()
    assert "Terraform will perform the following actions:" in captured.out


@pytest.mark.slow
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


@pytest.mark.slow
def test_output(local_stack):
    stack = local_stack(output=["content_sha256"])
    apply(stack, deploy=True)
    assert evaluate(stack.file.output["content_sha256"]) == sha256(b"world").hexdigest()


@pytest.mark.slow
def test_output_not_available(stack):
    stack.provider = TerraformProvider(
        name="consul",
    )
    stack.order = stack.provider.resource(
        type="consul_service",
        args=dict(
            name="foo",
            node="bar",
        ),
        output=["service_id"],
    )
    apply(stack, refresh=True)
    with pytest.raises(NotAvailable) as error:
        print(evaluate(stack.order.output["service_id"]))

    assert error.value.args == (
        "<TerraformResource order>: output 'service_id' not available",
    )


@pytest.mark.slow
def test_import_resource(stack):
    stack.time = TerraformResource(
        type="time_static",
        args={},
        output=["id"],
    )
    value = "2020-02-12T06:36:13Z"
    stack.time.import_resource(value)
    assert evaluate(stack.time.output["id"]) == value


@pytest.mark.slow
def test_provider_config(stack, tmp_path):
    stack.provider = TerraformProvider(
        name="tfcoremock",
        source="tfcoremock",
        version="~> 0.1.3",
        config=dict(
            resource_directory="opslib_resource_directory",
        ),
    )
    stack.resource = stack.provider.resource(
        type="tfcoremock_simple_resource",
        args=dict(
            number=13,
        ),
    )
    apply(stack, deploy=True)
    # XXX for some reason, Terraform quotes our directory name
    [outfile] = (stack.resource.tf_path / '"opslib_resource_directory"').iterdir()
    assert json.loads(outfile.read_text())["values"]["number"]["number"] == "13"


@pytest.mark.slow
def test_data_source(stack, tmp_path):
    path = tmp_path / "hello.txt"
    path.write_text("world")
    stack.provider = TerraformProvider(
        name="local",
        source="hashicorp/local",
        version="~> 2.3",
    )
    stack.source = stack.provider.data(
        type="local_file",
        args=dict(
            filename=str(path),
        ),
        output=["content"],
    )
    with pytest.raises(NotAvailable) as error:
        evaluate(stack.source.output["content"])
    assert error.value.args == (
        "<TerraformDataSource source>: output 'content' not available",
    )
    apply(stack, deploy=True)
    assert evaluate(stack.source.output["content"]) == "world"
