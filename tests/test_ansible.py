import sys

import pytest

from opslib.ansible import run_ansible
from opslib.results import OperationError


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
    assert result.output == "dont panic"
    assert result.stdout == ""
    assert result.stderr == "dont panic"
