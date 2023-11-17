import json
import os
from functools import cached_property
from typing import Optional

import click

from .components import Component
from .lazy import Lazy, NotAvailable, evaluate
from .local import run
from .props import Prop
from .results import Result
from .uptodate import UpToDate


def lazy_quote(value):
    return Lazy(lambda: evaluate(value).replace("${", "$${"))


class TerraformResult(Result):
    """
    The result of an invocation of ``terraform``. In addition to the fields
    inherited from :class:`~opslib.results.Result`, it contains the following:

    :ivar tf_result: The original :class:`~opslib.local.LocalRunResult` of
                     invoking the ``terraform`` command.
    """

    marker = "Terraform will perform the following actions:"

    def __init__(self, tf_result):
        self.tf_result = tf_result

        output = tf_result.stdout
        if self.marker in output:
            super().__init__(changed=True, output=output.split(self.marker)[1].strip())

        else:
            super().__init__(changed=False)


class TerraformProvider(Component):
    """
    The TerraformProvider component represents a Provider in the Terraform
    universe. After a provider is defined, :class:`TerraformResource`
    components can be created from it.

    :param name: The name of the provider, e.g. ``"aws"``.
    :param source: Provider source, e.g. ``"hashicorp/aws"``.
    :param version: Version requirement, e.g. ``"~> 4.0"`` (optional but highly
                    recommended).
    :param config: Provider configuration (optional). Most providers require
                   some level of configuration, although it can sometimes be
                   set through environment variables; consult each provider's
                   documentation for details.
    """

    class Props:
        name = Prop(str)
        source = Prop(Optional[str])
        version = Prop(Optional[str])
        config = Prop(Optional[dict])

    @cached_property
    def plugin_cache_path(self):
        return self._meta.statedir.path / "plugin-cache"

    @cached_property
    def config(self):
        provider_args = dict()
        if self.props.source:
            provider_args["source"] = self.props.source
        if self.props.version:
            provider_args["version"] = self.props.version

        config = dict(
            terraform=dict(
                required_providers={
                    self.props.name: provider_args,
                },
            ),
        )

        if self.props.config:
            config["provider"] = {self.props.name: self.props.config}

        return config

    def resource(self, **props):
        """
        Shorthand method to create a :class:`TerraformResource`, with
        ``provider`` set to this component.
        """

        return TerraformResource(
            provider=self,
            **props,
        )

    def data(self, **props):
        """
        Shorthand method to create a :class:`TerraformDataSource`, with
        ``provider`` set to this component.
        """

        return TerraformDataSource(
            provider=self,
            **props,
        )


class _TerraformComponent(Component):
    class Props:
        provider = Prop(Optional[TerraformProvider])
        type = Prop(str)
        args = Prop(dict, default={}, lazy=True)
        output = Prop(Optional[list])

    @property
    def address(self):
        return f"{self.props.type}.thing"

    @cached_property
    def tf_path(self):
        return self._meta.statedir.path / "terraform"

    def _run(self, *args, **kwargs):
        extra_env = {"TF_IN_AUTOMATION": "true"}
        provider = self.props.provider
        if provider and not os.environ.get("TF_PLUGIN_CACHE_DIR"):
            provider.plugin_cache_path.mkdir(exist_ok=True)
            extra_env["TF_PLUGIN_CACHE_DIR"] = str(provider.plugin_cache_path)

        return run("terraform", *args, **kwargs, cwd=self.tf_path, extra_env=extra_env)

    def _init(self):
        self.tf_path.mkdir(exist_ok=True, mode=0o700)
        (self.tf_path / "main.tf.json").write_text(json.dumps(self.config, indent=2))
        self._run("init", "-upgrade")  # XXX not concurrency safe
        self._init = lambda: None

    def run(self, *args, terraform_init=True, **kwargs):
        """
        Run the ``terraform`` command with the given arguments.
        """

        if terraform_init:
            self._init()
        return self._run(*args, **kwargs)

    @cached_property
    def _output_values(self):
        return json.loads(self.run("output", "-json", terraform_init=False).stdout)

    @cached_property
    def output(self):
        """
        Output values returned from Terraform.
        """

        def lazy_output(name):
            def get_value():
                try:
                    if not self.tf_path.exists():
                        raise KeyError

                    output = self._output_values[name]

                except KeyError:
                    raise NotAvailable(f"{self!r}: output {name!r} not available")

                return output["value"]

            return Lazy(get_value)

        return {name: lazy_output(name) for name in self.props.output}

    def add_commands(self, cli):
        @cli.forward_command
        def terraform(args):
            self.run(*args, capture_output=False, exit=True)


class TerraformResource(_TerraformComponent):
    """
    The TerraformResource component creates a single Resource through
    Terraform.

    :param provider: The :class:`TerraformProvider` for this resource.
                     Technically optional because some builtin resource types
                     of Terraform don't belong to any provider.
    :param type: Type of resource, e.g. ``"aws_vpc"``.
    :param args: Arguments of the resource (:class:`dict`). Consult the
                 provider's documentation for the arguments supported by each
                 resource. May be :class:`~opslib.lazy.Lazy`.
    :param output: List of attributes exported by the resource to be fetched
                   from Terraform. They are available on the ``output``
                   property. (optional)
    """

    uptodate = UpToDate()

    @property
    @uptodate.snapshot
    def config(self):
        provider = self.props.provider
        config = dict(
            provider.config if provider else {},
            resource={
                self.props.type: {
                    "thing": evaluate(self.props.args),
                },
            },
        )

        if self.props.output:
            config["output"] = {
                key: {
                    "value": f"${{{self.address}.{key}}}",
                    "sensitive": True,
                }
                for key in self.props.output
            }

        return config

    @uptodate.refresh
    def refresh(self):
        self.run("refresh")
        return TerraformResult(self.run("plan"))

    def _apply(self, dry_run=False, destroy=False):
        args = ["plan"] if dry_run else ["apply", "-auto-approve"]
        if destroy:
            args.append("-destroy")
        return TerraformResult(self.run(*args, "-refresh=false"))

    @uptodate.deploy
    def deploy(self, dry_run=False):
        return self._apply(dry_run=dry_run)

    @uptodate.destroy
    def destroy(self, dry_run=False):
        return self._apply(dry_run=dry_run, destroy=True)

    def import_resource(self, resource_id, **kwargs):
        """
        Import an existing resource into Terraform.
        """

        return self.run("import", self.address, evaluate(resource_id), **kwargs)

    def add_commands(self, cli):
        super().add_commands(cli)

        @cli.command("import")
        @click.argument("resource_id")
        def import_(resource_id):
            self.import_resource(resource_id, capture_output=False, exit=True)

        @cli.command
        def forget():
            self.run("state", "rm", self.address)


class TerraformDataSource(_TerraformComponent):
    """
    The TerraformDataSource component retrieves data through a Terraform data
    source.

    :param provider: The :class:`TerraformProvider` for this data source.
                     Technically optional because some builtin data source
                     types of Terraform don't belong to any provider.
    :param type: Type of data source, e.g. ``"aws_vpc"``.
    :param args: Arguments of the data source (:class:`dict`). Consult the
                 provider's documentation for the arguments supported by each
                 data source. May be :class:`~opslib.lazy.Lazy`.
    :param output: List of attributes exported by the data source to be fetched
                   from Terraform. They are available on the ``output``
                   property. (optional)
    """

    uptodate = UpToDate()

    @property
    @uptodate.snapshot
    def config(self):
        provider = self.props.provider
        config = dict(
            provider.config if provider else {},
            data={
                self.props.type: {
                    "thing": evaluate(self.props.args),
                },
            },
        )

        if self.props.output:
            config["output"] = {
                key: {
                    "value": f"${{data.{self.address}.{key}}}",
                    "sensitive": True,
                }
                for key in self.props.output
            }

        return config

    @uptodate.refresh
    def refresh(self):
        self.run("refresh")
        return TerraformResult(self.run("plan"))

    @uptodate.deploy
    def deploy(self, dry_run=False):
        if dry_run:
            return Result(changed=True)

        return self.refresh()
