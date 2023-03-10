import logging
from warnings import warn

from ansible.executor.task_queue_manager import TaskQueueManager
from ansible.inventory.manager import InventoryManager
from ansible.parsing.dataloader import DataLoader
from ansible.playbook.play import Play
from ansible.plugins.callback import CallbackBase
from ansible.vars.manager import VariableManager

from .results import Result

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
        self.stdout = data.get("stdout", "")
        self.stderr = data.get("stderr", "")
        for warning in data.get("warnings", []):
            warn(warning)

        super().__init__(
            changed=bool(data.get("changed")),
            output=self.stderr + self.stdout,
            failed=failed,
        )


def run_ansible(hostname, ansible_variables, action):
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
