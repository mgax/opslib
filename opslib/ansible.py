import logging
from collections.abc import Callable
from typing import Optional
from warnings import warn

from ansible import context
from ansible.executor.task_queue_manager import TaskQueueManager
from ansible.inventory.manager import InventoryManager
from ansible.module_utils.common.collections import ImmutableDict
from ansible.parsing.dataloader import DataLoader
from ansible.playbook.play import Play
from ansible.plugins.callback import CallbackBase
from ansible.vars.manager import VariableManager

from .lazy import evaluate
from .props import Prop
from .results import Result
from .things import Thing

logger = logging.getLogger(__name__)


class StdoutCallback(CallbackBase):
    def __init__(self):
        self.results = []
        self.errors = False

    def v2_runner_on_ok(self, result):
        self.results.append(result._result)

    def v2_runner_on_unreachable(self, result):
        self.errors = True
        self.results.append(result._result)

    def v2_runner_on_failed(self, result, **kwargs):
        self.errors = True
        self.results.append(result._result)


class AnsibleResult(Result):
    def __init__(self, data, failed):
        self.data = data
        self.exception = data.get("exception", "")
        if self.exception:
            self.exception += "\n"
        self.msg = data.get("msg", "")
        if self.msg:
            self.msg += "\n"
        self.stdout = data.get("stdout", "")
        self.stderr = data.get("stderr", "")

        output = self.msg + self.exception + self.stderr + self.stdout

        for warning in data.get("warnings", []):
            warn(warning)

        super().__init__(
            changed=bool(data.get("changed")),
            output=output,
            failed=failed,
        )


def run_ansible(hostname, ansible_variables, action, check=False):
    context.CLIARGS = ImmutableDict(
        connection="smart",
        check=check,
        diff=True,
        verbosity=0,
    )

    loader = DataLoader()
    inventory = InventoryManager(loader=loader, sources=f"{hostname},")
    variable_manager = VariableManager(loader=loader, inventory=inventory)
    for name, value in ansible_variables:
        variable_manager.set_host_variable(hostname, name, value)

    stdout_callback = StdoutCallback()
    task_queue_manager = TaskQueueManager(
        inventory=inventory,
        variable_manager=variable_manager,
        loader=loader,
        passwords={},
        stdout_callback=stdout_callback,
    )

    play = Play().load(
        dict(
            hosts=[hostname],
            gather_facts="no",
            tasks=[{"action": action}],
        ),
        variable_manager=variable_manager,
        loader=loader,
    )

    try:
        task_queue_manager.run(play)

    finally:
        task_queue_manager.cleanup()
        loader.cleanup_all_tmp_files()

    result = AnsibleResult(stdout_callback.results[-1], stdout_callback.errors)
    result.raise_if_failed("Ansible failed")
    return result


class AnsibleAction(Thing):
    class Props:
        hostname = Prop(str)
        ansible_variables = Prop(list)
        module = Prop(str)
        args = Prop(dict)
        format_output = Prop(Optional[Callable])

    def run(self, check=False):
        result = run_ansible(
            hostname=self.props.hostname,
            ansible_variables=self.props.ansible_variables,
            action=dict(
                module=self.props.module,
                args=evaluate(self.props.args),
            ),
            check=check,
        )
        if self.props.format_output:
            result.output = self.props.format_output(result)
        return result

    def deploy(self, dry_run=False):
        return self.run(check=dry_run)
