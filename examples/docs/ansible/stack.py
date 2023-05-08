from opslib import LocalHost, Stack, run
from opslib.ansible import AnsibleAction


def diffstat(result):
    diff = result.data["diff"]["prepared"]
    if result.data["before"]:
        diff = run("diffstat", "-C", input=diff).stdout
    return diff


stack = Stack(__name__)
stack.host = LocalHost()
stack.repo = AnsibleAction(
    host=stack.host,
    module="ansible.builtin.git",
    args=dict(
        repo="https://github.com/mgax/opslib",
        dest="/tmp/opslib",
    ),
    format_output=diffstat,
)
