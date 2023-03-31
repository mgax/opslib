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
        provider_body = dict()
        if self.props.source:
            provider_body["source"] = self.props.source
        if self.props.version:
            provider_body["version"] = self.props.version

        config = dict(
            terraform=dict(
                required_providers={
                    self.props.name: provider_body,
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


class TerraformResource(Component):
    """
    The TerraformResource component creates a single Resource through
    Terraform.

    :param provider: The :class:`TerraformProvider` for this resource.
                     Technically optional because some builtin resource types
                     of Terraform don't belong to any provider.
    :param type: Type of resource, e.g. ``"aws_vpc"``.
    :param body: Arguments of the resource (:class:`dict`). Consult the
                 provider's documentation for the arguments supported by each
                 resource.
    :param output: List of attributes exported by the resource to be fetched
                   from Terraform. They are available on the ``output``
                   property. (optional)
    """

    class Props:
        provider = Prop(Optional[TerraformProvider])
        type = Prop(str)
        body = Prop(dict)
        output = Prop(Optional[list])

    uptodate = UpToDate()

    @cached_property
    def tf_path(self):
        return self._meta.statedir.path / "terraform"

    @property
    @uptodate.snapshot
    def config(self):
        provider = self.props.provider
        config = dict(
            provider.config if provider else {},
            resource={
                self.props.type: {
                    "thing": evaluate(self.props.body),
                },
            },
        )

        if self.props.output:
            config["output"] = {
                key: {
                    "value": f"${{{self.props.type}.thing.{key}}}",
                    "sensitive": True,
                }
                for key in self.props.output
            }

        return config

    def _run(self, *args, **kwargs):
        extra_env = {"TF_IN_AUTOMATION": "true"}
        provider = self.props.provider
        if provider and not os.environ.get("TF_PLUGIN_CACHE_DIR"):
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

    @uptodate.refresh
    def refresh(self):
        self.run("refresh")
        return TerraformResult(self.run("plan"))

    @uptodate.deploy
    def deploy(self, dry_run=False):
        args = ["plan"] if dry_run else ["apply", "-auto-approve"]
        return TerraformResult(self.run(*args, "-refresh=false"))

    def import_resource(self, resource_id):
        """
        Import an existing resource into Terraform.
        """

        return self.run("import", f"{self.props.type}.thing", evaluate(resource_id))

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
                    output = self._output_values[name]

                except KeyError:
                    raise NotAvailable(f"{self!r}: output {name!r} not available")

                return output["value"]

            return Lazy(get_value)

        return {name: lazy_output(name) for name in self.props.output}

    def add_commands(self, cli):
        @cli.command(
            context_settings=dict(
                ignore_unknown_options=True,
                allow_interspersed_args=False,
            )
        )
        @click.argument("args", nargs=-1, type=click.UNPROCESSED)
        def terraform(args):
            self.run(*args, capture_output=False, exit=True)
