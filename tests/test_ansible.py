import sys

import pytest

from opslib.ansible import AnsibleAction, run_ansible
from opslib.operations import apply
from opslib.places import LocalHost
from opslib.results import OperationError
from opslib.things import init_statedir


def run_local_ansible(action):
    return run_ansible(
        hostname="localhost",
        ansible_variables=[
            ("ansible_connection", "local"),
            ("ansible_python_interpreter", sys.executable),
        ],
        action=action,
    )


def test_hello_world():
    result = run_local_ansible(
        action=dict(
            module="ansible.builtin.shell",
            args=dict(cmd="echo hello world"),
        ),
    )

    assert result.changed
    assert not result.failed
    assert result.output == "hello world"
    assert result.stdout == "hello world"
    assert result.stderr == ""


def test_errors():
    with pytest.raises(OperationError) as error:
        run_local_ansible(
            action=dict(
                module="ansible.builtin.shell",
                args=dict(cmd="echo dont panic >&2; false"),
            ),
        )

    result = error.value.result
    assert result.changed
    assert result.failed
    assert result.output == "non-zero return code\ndont panic"
    assert result.stdout == ""
    assert result.stderr == "dont panic"


def test_ansible_action(tmp_path, Stack):
    foo_path = tmp_path / "foo"
    stack = Stack()
    host = LocalHost()
    stack.action = AnsibleAction(
        hostname=host.hostname,
        ansible_variables=host.ansible_variables,
        module="ansible.builtin.file",
        args=dict(
            path=str(foo_path),
            state="directory",
        ),
    )
    init_statedir(stack)
    apply(stack, deploy=True)
    assert foo_path.is_dir()
