import json
from collections.abc import Callable
from contextlib import contextmanager
from datetime import timedelta
from functools import cached_property

import click

from opslib.components import Component
from opslib.lazy import Lazy
from opslib.props import Prop
from opslib.results import OperationError, Result
from opslib.state import JsonState

from .http import HttpClient


class TailscaleNetwork(Component):
    class Props:
        api_key = Prop(str)

    @cached_property
    def api(self):
        return HttpClient(
            "https://api.tailscale.com/api/v2",
            auth=(self.props.api_key, ""),
        )

    def create_key(self, expire):
        result = self.api.post(
            "/tailnet/-/keys",
            json=dict(
                capabilities=dict(
                    devices=dict(
                        create=dict(
                            reusable=False,
                            ephemeral=False,
                            preauthorized=False,
                        ),
                    ),
                ),
                expirySeconds=int(expire.total_seconds()),
            ),
        )
        return result.json["key"]

    def delete_key(self, key):
        key_id = key.split("-")[2]
        self.api.delete(f"/tailnet/-/keys/{key_id}")

    @contextmanager
    def auth_key(self, expire=timedelta(minutes=1)):
        key = self.create_key(expire)
        try:
            yield key

        finally:
            self.delete_key(key)

    def node(self, **props):
        return TailscaleNode(
            network=self,
            **props,
        )


class TailscaleNode(Component):
    class Props:
        network = Prop(TailscaleNetwork)
        run = Prop(Callable)

    state = JsonState()

    def refresh(self):
        node_id = self._get_node_id()

        if node_id == self.node_id:
            return Result()

        self.state["node_id"] = node_id
        return Result(changed=True, output=f"node_id = {node_id!r}")

    def deploy(self, dry_run=False):
        if self.node_id:
            return Result()

        if dry_run:
            return Result(changed=True)

        def deferred_deploy():
            self.props.run(
                input="curl -fsSL https://tailscale.com/install.sh | sh",
                capture_output=False,
            )

            with self.props.network.auth_key() as tskey:
                click.echo("Running tailscale up ...")
                self.props.run("tailscale", "up", "--authkey", tskey)

            click.echo("Refreshing state ...")
            self.refresh()

            click.echo("Done.")
            return Result(changed=True)

        return Lazy(deferred_deploy)

    def _get_node_id(self):
        try:
            status_json = self.props.run("tailscale", "status", "--json").stdout

        except OperationError as error:
            if "tailscale: command not found" in error.result.stderr:
                return None

            raise

        return json.loads(status_json)["Self"]["ID"] or None

    @property
    def node_id(self):
        return self.state.get("node_id")

    def add_commands(self, cli):
        @cli.forward_command
        def run(args):
            self.props.run("tailscale", *args, capture_output=False, exit=True)
