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

from .callbacks import Callbacks
from .components import Component
from .lazy import evaluate
from .places import BaseHost
from .props import Prop
from .results import Result
from .uptodate import UpToDate

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
    """
    The result of an :class:`AnsibleAction`, or a call to :func:`run_ansible`.
    In addition to the fields inherited from :class:`~opslib.results.Result`,
    it contains the following:

    :ivar data: The original result object reported by Ansible. The format
                varies quite a bit from module to module.
    :ivar exception: If the action failed, this contains the stack trace from
                     Ansible, as :class:`str`.
    :ivar msg: If the action failed, this contains the error message from
            Ansible.
    :ivar stdout: The ``stdout`` field from ``data``.
    :ivar stderr: The ``stderr`` field from ``data``.
    """

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
    """
    Invoke Ansible with a single action. This creates and executes an Ansible
    Play, with a single host, and a single task that contains the given action.
    Returns an :class:`AnsibleResult` object.

    Instead of directly calling this function, typically one would create an
    :class:`AnsibleAction` in the stack, but it's usable directly if need be.
    It encapsulates all setup and teardown of the Ansible machinery and exposes
    only the essential arguments.

    :param hostname: Name of the host to act on.
    :param ansible_variables: List of variables to configure Ansible.
    :param action: The Ansible action. It should be a dictionary with members
                   *module* and *args*.
    :param check: If ``True``, run Ansible in "check" mode, which will not
                  apply any changes, just show differences.
    """

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

    if check and not stdout_callback.results:
        # XXX the module likely doesn't support "check" mode
        return Result(changed=True)

    result = AnsibleResult(stdout_callback.results[-1], stdout_callback.errors)
    result.raise_if_failed("Ansible failed")
    return result


class AnsibleAction(Component):
    """
    The AnsibleAction component executes an Ansible module.

    :param host: :class:`~opslib.places.BaseHost` to act on.
    :param module: Name of the Ansible module to invoke, e.g.
                   ``"ansible.builtin.copy"``.
    :param args: Dictionary of arguments for the module. Consult each module's
                 documentation for the args (or *Parameters*) it supports.
    :param format_output: Optional callback used to format the result output.
                          If provided, it will be called with a single
                          parameter, the :class:`AnsibleResult` object; its
                          return value will be used to overwrite the ``output``
                          attribute of the result.
    """

    class Props:
        host = Prop(BaseHost)
        module = Prop(str)
        args = Prop(dict)
        format_output = Prop(Optional[Callable])

    uptodate = UpToDate()
    on_change = Callbacks()

    @property
    def action(self):
        return dict(
            module=self.props.module,
            args=evaluate(self.props.args),
        )

    @uptodate.snapshot
    def _get_ansible_args(self):
        return dict(
            hostname=evaluate(self.props.host.hostname),
            ansible_variables=self.props.host.ansible_variables,
            action=self.action,
        )

    def run(self, check=False):
        """
        Call :func:`run_ansible` with the action defined by this component.
        """

        if not check:
            self.on_change.invoke()

        result = run_ansible(
            **self._get_ansible_args(),
            check=check,
        )
        if result.changed and self.props.format_output:
            result.output = self.props.format_output(result)
        return result

    @uptodate.refresh
    def refresh(self):
        return self.run(check=True)

    @uptodate.deploy
    def deploy(self, dry_run=False):
        return self.run(check=dry_run)
