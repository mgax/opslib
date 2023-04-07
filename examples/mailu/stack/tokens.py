import secrets
from typing import Optional

from opslib.components import Component
from opslib.lazy import NotAvailable, lazy_property
from opslib.props import Prop
from opslib.results import Result
from opslib.state import JsonState


class RandomToken(Component):
    class Props:
        length = Prop(Optional[int])

    state = JsonState()

    def _generate(self):
        value = secrets.token_urlsafe()
        if self.props.length:
            value = value[: self.props.length]
        return value

    def deploy(self, dry_run=True):
        if self.state.get("value"):
            return Result()

        if not dry_run:
            self.state["value"] = self._generate()

        return Result(changed=True)

    @lazy_property
    def value(self):
        value = self.state.get("value")
        if value is None:
            raise NotAvailable(f"Value for {self} has not been generated yet")
        return value

    def add_commands(self, cli):
        @cli.command()
        def clear():
            self.state["value"] = None
