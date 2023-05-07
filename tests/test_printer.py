from textwrap import dedent

import pytest

from opslib.components import Component
from opslib.lazy import Lazy
from opslib.local import run
from opslib.operations import AbortOperation, apply, print_report
from opslib.props import Prop
from opslib.results import Result


class Task(Component):
    class Props:
        changed = Prop(bool, default=False)
        failed = Prop(bool, default=False)
        exception = Prop(bool, default=False)

    def deploy(self, dry_run=False):
        if self.props.exception:
            run("bash", "-c", "echo dont panic >&2; false")

        return Result(
            changed=self.props.changed,
            failed=self.props.failed,
        )


def test_print_ok(capsys, stack):
    stack.task = Task(changed=False)

    apply(stack, deploy=True)

    captured = capsys.readouterr()
    assert captured.out == "task Task ...\ntask Task [ok]\n"
    assert captured.err == ""


def test_print_changed(capsys, stack):
    stack.task = Task(changed=True)

    apply(stack, deploy=True)

    captured = capsys.readouterr()
    assert captured.out == "task Task ...\ntask Task [changed]\n"
    assert captured.err == ""


def test_print_failed(capsys, stack):
    stack.task = Task(failed=True)

    apply(stack, deploy=True)

    captured = capsys.readouterr()
    assert captured.out == "task Task ...\ntask Task [failed]\n"
    assert captured.err == ""


def test_print_error(capsys, stack):
    stack.task = Task(exception=True)

    with pytest.raises(AbortOperation):
        apply(stack, deploy=True)

    captured = capsys.readouterr()
    assert captured.out == "task Task ...\ntask Task [failed]\ndont panic\n\n"
    assert captured.err == "Operation failed!\n"


def test_print_direct_output(capfd, stack):
    class DirectOutputTask(Component):
        def deploy(self, dry_run=False):
            return Lazy(run, "echo", "hello lazy", capture_output=False)

    stack.task = DirectOutputTask()
    apply(stack, deploy=True)

    captured = capfd.readouterr()
    assert captured.out == dedent(
        """\
        task DirectOutputTask ...
        hello lazy
        task DirectOutputTask [changed]
        """
    )


def test_print_report(capsys, stack):
    stack.a = Task()
    stack.b = Task(changed=True)
    stack.c = Task(failed=True)
    results = apply(stack, deploy=True)
    print_report(results)
    captured = capsys.readouterr()
    assert captured.out == dedent(
        """\
        a Task ...
        a Task [ok]
        b Task ...
        b Task [changed]
        c Task ...
        c Task [failed]
        1 ok
        1 changed
        1 failed
        <class 'test_printer.Task'>: 2
        """
    )
