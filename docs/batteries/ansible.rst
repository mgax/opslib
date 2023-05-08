Ansible wrapper
===============

The :mod:`opslib.ansible` module runs Ansible actions. The `Ansible.Builtin`_
collection is installed by default.

.. _Ansible.Builtin: https://docs.ansible.com/ansible/latest/collections/ansible/builtin/index.html

AnsibleAction component
-----------------------

:class:`~opslib.ansible.AnsibleAction` runs a single Ansible action on a single host.

After a successful deployment, the component instance is marked as "up to
date", and will be skipped in subsequent deployments, unless any of the props
change. To check if remote state has changed, run ``opslib - diff``.

.. code-block:: python

    from opslib import LocalHost, Stack
    from opslib.ansible import AnsibleAction

    stack = Stack(__name__)
    stack.host = LocalHost()
    stack.repo = AnsibleAction(
        host=stack.host,
        module="ansible.builtin.git",
        args=dict(
            repo="https://github.com/mgax/opslib",
            dest="/tmp/opslib",
        ),
    )

Formatting output
~~~~~~~~~~~~~~~~~

Ansible returns rich output from actions, including data about differences
between desired and actual state, but there doesn't seem to be a uniform
structure across modules. However, you can specify a *format_output* prop:

.. code-block:: python

    from opslib import run

    def diffstat(result):
        diff = result.data["diff"]["prepared"]
        if result.data["before"]:
            diff = run("diffstat", "-C", input=diff).stdout
        return diff

    stack.repo = AnsibleAction(
        host=stack.host,
        module="ansible.builtin.git",
        args=dict(
            repo="https://github.com/mgax/opslib",
            dest="/tmp/opslib",
        ),
        format_output=diffstat,
    )

Invoking Ansible directly
-------------------------

:func:`~opslib.ansible.run_ansible` is a standalone function that runs an
Ansible action. It doesn't depend on a stack being present and is a handy way
to invoke Ansible and get an :class:`~opslib.ansible.AnsibleResult` object
back.

.. code-block:: python

    import sys
    from pprint import pprint
    from opslib.ansible import run_ansible

    result = run_ansible(
        hostname="localhost",
        ansible_variables=[
            ("ansible_connection", "local"),
            ("ansible_python_interpreter", sys.executable),
        ],
        action=dict(
            module="ansible.builtin.gather_facts",
        ),
    )
    pprint(result.data)
