import json
import os
from functools import cached_property

import click

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
        version = Prop(str)

    @cached_property
    def plugin_cache_path(self):
        return self._meta.statedir.path / "plugin-cache"

    @cached_property
    def config(self):
        return dict(
            terraform=dict(
                required_providers={
                    self.props.name: {
                        "source": self.props.source,
                        "version": self.props.version,
                    },
                },
            ),
        )

    def resource(self, **props):
        return TerraformResource(
            provider=self,
            **props,
        )


class TerraformResource(Thing):
    class Props:
        provider = Prop(TerraformProvider)
        type = Prop(str)
        body = Prop(dict)

    @cached_property
    def tf_path(self):
        return self._meta.statedir.path / "terraform"

    def _run(self, *args, **kwargs):
        extra_env = {"TF_IN_AUTOMATION": "true"}
        if not os.environ.get("TF_PLUGIN_CACHE_DIR"):
            extra_env["TF_PLUGIN_CACHE_DIR"] = str(
                self.props.provider.plugin_cache_path
            )

        return run("terraform", *args, **kwargs, cwd=self.tf_path, extra_env=extra_env)

    def _init(self):
        self.tf_path.mkdir(exist_ok=True, mode=0o700)
        config = dict(
            self.props.provider.config,
            resource={
                self.props.type: {
                    "thing": self.props.body,
                },
            },
        )
        (self.tf_path / "main.tf.json").write_text(json.dumps(config, indent=2))
        self._run("init")  # XXX not concurrency safe
        self._init = lambda: None

    def run(self, *args, **kwargs):
        self._init()
        return self._run(*args, **kwargs)

    def deploy(self, dry_run=False):
        return TerraformResult(self.run("apply", "-refresh=false", "-auto-approve"))

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
