import json
import os
from functools import cached_property
from typing import Optional

import click

from .lazy import Lazy, evaluate
from .local import run
from .props import Prop
from .results import Result
from .things import Thing


class TerraformResult(Result):
    marker = "Terraform will perform the following actions:"

    def __init__(self, tf_result):
        self.tf_result = tf_result

        output = tf_result.stdout
        if self.marker in output:
            super().__init__(changed=True, output=output.split(self.marker)[1].strip())

        else:
            super().__init__(changed=False)


class TerraformProvider(Thing):
    class Props:
        name = Prop(str)
        source = Prop(str)
        version = Prop(Optional[str])
        config = Prop(Optional[dict])

    @cached_property
    def plugin_cache_path(self):
        return self._meta.statedir.path / "plugin-cache"

    @cached_property
    def config(self):
        provider_body = dict(
            source=self.props.source,
        )
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
        return TerraformResource(
            provider=self,
            **props,
        )


class TerraformResource(Thing):
    class Props:
        provider = Prop(Optional[TerraformProvider])
        type = Prop(str)
        body = Prop(dict)
        output = Prop(Optional[list])

    @cached_property
    def tf_path(self):
        return self._meta.statedir.path / "terraform"

    def _run(self, *args, **kwargs):
        extra_env = {"TF_IN_AUTOMATION": "true"}
        provider = self.props.provider
        if provider and not os.environ.get("TF_PLUGIN_CACHE_DIR"):
            extra_env["TF_PLUGIN_CACHE_DIR"] = str(provider.plugin_cache_path)

        return run("terraform", *args, **kwargs, cwd=self.tf_path, extra_env=extra_env)

    def _init(self):
        self.tf_path.mkdir(exist_ok=True, mode=0o700)
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

        (self.tf_path / "main.tf.json").write_text(json.dumps(config, indent=2))
        self._run("init")  # XXX not concurrency safe
        self._init = lambda: None

    def run(self, *args, **kwargs):
        self._init()
        return self._run(*args, **kwargs)

    def refresh(self):
        return TerraformResult(self.run("refresh"))

    def deploy(self, dry_run=False):
        args = ["plan"] if dry_run else ["apply", "-auto-approve"]
        return TerraformResult(self.run(*args, "-refresh=false"))

    def import_resource(self, resource_id):
        return self.run("import", f"{self.props.type}.thing", evaluate(resource_id))

    @cached_property
    def _output_values(self):
        return json.loads(self.run("output", "-json").stdout)

    @cached_property
    def output(self):
        def lazy_output(name):
            return Lazy(lambda: self._output_values[name]["value"])

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
